from pathlib import Path
import hashlib
import json
import re
from src.config import ROOT, Settings
from src.embeddings import MiniLMEmbeddings


def split_document(text, size=220, overlap=40):
    """Heading-aware overlapping word chunks; full text remains in metadata."""
    heading = "Introduction"
    for section in re.split(r"(?m)(?=^## )", text):
        lines = section.strip().splitlines()
        if not lines:
            continue
        if lines[0].startswith("#"):
            heading = lines[0].lstrip("# ")
        words = section.split()
        for start in range(0, len(words), size - overlap):
            chunk = " ".join(words[start:start + size])
            if len(chunk) > 40:
                yield heading, chunk
            if start + size >= len(words):
                break


def plain(value):
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return dict(value)


class KnowledgeBase:
    """Pinecone is the only production vector store; test doubles are explicit."""

    def __init__(self, settings=None, *, index=None, embeddings=None):
        self.settings = settings or Settings()
        self.embeddings = embeddings or MiniLMEmbeddings()
        self._index = index
        self._client = None
        self.records, self.document_count = self._load_resources()
        identity = json.dumps({"model": self.embeddings.model_name, "records": self.records}, sort_keys=True)
        version = hashlib.sha256(identity.encode()).hexdigest()[:12]
        # Changed resources get a new namespace; unrelated remote data is not deleted.
        self.namespace = f"{self.settings.pinecone_namespace}-{version}"

    @property
    def configured(self):
        return self._index is not None or bool(self.settings.pinecone_api_key and self.settings.pinecone_host)

    def _connect(self):
        if not self.configured:
            raise ValueError("Set PINECONE_API_KEY and PINECONE_INDEX_HOST in Solution/.env before uploading or searching.")
        if self._index is None:
            from pinecone import Pinecone
            self._client = Pinecone(api_key=self.settings.pinecone_api_key, timeout=30)
            self._index = self._client.index(host=self.settings.pinecone_host)
        return self._index

    @staticmethod
    def _load_resources():
        manifest = json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8"))
        if len({item["id"] for item in manifest}) < 5:
            raise ValueError("At least five distinct knowledge resources are required.")
        records = []
        for item in manifest:
            path = (ROOT / item["path"]).resolve()
            if not path.is_relative_to(ROOT / "data/knowledge"):
                raise ValueError("Knowledge files must be under data/knowledge.")
            text = path.read_text(encoding="utf-8")
            for i, (heading, chunk) in enumerate(split_document(text)):
                records.append({"id": f'{item["id"]}:{i+1}', "metadata": {
                    "source_id": item["id"], "title": item["title"], "path": item["path"],
                    "heading": heading, "chunk": i + 1, "text": chunk,
                    "synthetic": bool(item["synthetic"]), "version": item["version"],
                    "embedding_model": MiniLMEmbeddings.model_name,
                    "sha256": hashlib.sha256(text.encode()).hexdigest()}})
        return records, len(manifest)

    def status(self):
        if not self.configured:
            return {"state": "not_configured", "indexed_chunks": None,
                    "message": "Pinecone connection details have not been supplied."}
        try:
            stats = plain(self._connect().describe_index_stats())
            dimension = int(stats.get("dimension", 0))
            if dimension != self.embeddings.dimension or stats.get("metric") not in {None, "cosine"}:
                return {"state": "error", "indexed_chunks": None,
                        "message": "The Pinecone vector index must use 384 dimensions and cosine similarity."}
            ns = plain(stats.get("namespaces", {}).get(self.namespace, {}))
            return {"state": "connected", "indexed_chunks": int(ns.get("vector_count", 0)),
                    "namespace": self.namespace, "dimension": dimension}
        except Exception:
            return {"state": "error", "indexed_chunks": None,
                    "message": "Pinecone could not be reached. Check index host, key, permissions and network."}

    def ingest(self):
        index = self._connect()  # Fail before downloads if connection details are absent.
        status = self.status()
        if status["state"] != "connected":
            raise ValueError(status["message"])
        vectors = self.embeddings.encode([r["metadata"]["text"] for r in self.records])
        uploaded = 0
        for start in range(0, len(self.records), 50):
            batch = [{**r, "values": vector} for r, vector in
                     zip(self.records[start:start+50], vectors[start:start+50])]
            response = plain(index.upsert(vectors=batch, namespace=self.namespace))
            count = int(response.get("upserted_count", 0))
            if count != len(batch):
                raise ValueError("Pinecone did not confirm the complete batch; retry ingestion.")
            uploaded += count
        return {"documents": self.document_count, "uploaded_chunks": uploaded,
                "embedding_model": self.embeddings.model_name, "dimensions": self.embeddings.dimension,
                "store": "Pinecone", "namespace": self.namespace,
                "note": "Upserts acknowledged; query visibility is eventually consistent."}

    def search(self, query, top_k=4):
        if not query.strip():
            return {"sources": [], "message": "A search question is required."}
        if not self.configured:
            return {"error": "Pinecone is not configured. Add connection details to .env, then ingest the documents.", "sources": []}
        try:
            vector = self.embeddings.encode([query])[0]
            result = plain(self._connect().query(vector=vector, top_k=max(1, min(top_k, 10)),
                namespace=self.namespace, include_metadata=True, include_values=False))
            sources = []
            for match in result.get("matches", []):
                match = plain(match)
                score = float(match.get("score", 0))
                meta = match.get("metadata", {})
                if score >= 0.25 and meta.get("embedding_model") == self.embeddings.model_name:
                    sources.append({**meta, "citation": match["id"], "similarity": round(score, 4)})
            return {"sources": sources, "instruction": "Use only supporting passages; cite [source:chunk].",
                    "message": "No supporting passages found. Check ingestion and allow for Pinecone consistency." if not sources else ""}
        except Exception:
            return {"error": "Pinecone retrieval failed. Check connection, index dimensions and ingestion.", "sources": []}

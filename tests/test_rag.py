"""Offline tests use a named double; no production in-memory fallback exists."""
import math
import pytest
from src.rag import KnowledgeBase, split_document, plain
from src.embeddings import MiniLMEmbeddings


class OfflineIndexDouble:
    def __init__(self, dimension=384):
        self.dimension = dimension
        self.rows = {}
        self.last_query = None

    def describe_index_stats(self):
        return {"dimension": self.dimension, "namespaces": {
            ns: {"vector_count": len(rows)} for ns, rows in self.rows.items()}}

    def upsert(self, vectors, namespace):
        rows = self.rows.setdefault(namespace, {})
        for vector in vectors:
            rows[vector["id"]] = vector
        return {"upserted_count": len(vectors)}

    def query(self, vector, top_k, namespace, include_metadata, include_values):
        self.last_query = {"namespace": namespace, "include_metadata": include_metadata}
        matches = []
        for item in self.rows.get(namespace, {}).values():
            score = sum(a*b for a,b in zip(vector, item["values"]))
            matches.append({"id": item["id"], "score": score, "metadata": item["metadata"]})
        return {"matches": sorted(matches, key=lambda x: -x["score"])[:top_k]}


@pytest.fixture(scope="module")
def kb():
    index = OfflineIndexDouble()
    knowledge = KnowledgeBase(index=index)
    knowledge.ingest()
    return knowledge


@pytest.mark.parametrize("query,expected", [
    ("Windows 11 Campus-Lab Wi-Fi connection airplane mode", "WIFI"),
    ("VPN tunnel connected internal resource inaccessible authorized client", "VPN"),
    ("Account locked five failed attempts fifteen minutes password recovery", "ACCOUNTS"),
    ("Printer offline stalled queue cancel own print job", "PRINT"),
    ("Priority P1 response target widespread essential shared service", "POLICY")])
def test_real_embeddings_and_pinecone_query_contract(kb, query, expected):
    sources = kb.search(query)["sources"]
    assert sources and sources[0]["source_id"] == expected
    assert all(source["citation"].startswith(source["source_id"] + ":") for source in sources)
    assert kb._index.last_query == {"namespace": kb.namespace, "include_metadata": True}


def test_upserts_are_idempotent_and_corpus_is_namespaced(kb):
    before = kb.status()["indexed_chunks"]
    result = kb.ingest()
    assert result["documents"] == 5
    assert before == result["uploaded_chunks"] == kb.status()["indexed_chunks"]
    assert result["store"] == "Pinecone"


def test_missing_configuration_does_not_fall_back_to_local_database(settings):
    settings.pinecone_api_key = ""
    settings.pinecone_host = ""
    empty = KnowledgeBase(settings)
    assert empty.status()["state"] == "not_configured"
    assert "error" in empty.search("wifi")
    with pytest.raises(ValueError, match="PINECONE_API_KEY"):
        empty.ingest()


def test_wrong_dimension_is_rejected_before_upload():
    knowledge = KnowledgeBase(index=OfflineIndexDouble(dimension=1536))
    assert knowledge.status()["state"] == "error"
    with pytest.raises(ValueError, match="384"):
        knowledge.ingest()


def test_wrong_reported_metric_is_rejected():
    index = OfflineIndexDouble()
    index.describe_index_stats = lambda: {"dimension": 384, "metric": "euclidean", "namespaces": {}}
    assert KnowledgeBase(index=index).status()["state"] == "error"


def test_actual_sdk_response_types_are_decoded():
    from pinecone import UpsertResponse, QueryResponse, DescribeIndexStatsResponse
    assert plain(UpsertResponse(upserted_count=2))["upserted_count"] == 2
    assert plain(QueryResponse(matches=[]))["matches"] == []
    assert plain(DescribeIndexStatsResponse(dimension=384, namespaces={}))["dimension"] == 384


def test_empty_index_and_query(kb):
    knowledge = KnowledgeBase(index=OfflineIndexDouble())
    assert knowledge.search("wifi")["sources"] == []
    assert kb.search("")["sources"] == []


def test_model_mismatch_is_not_used_as_evidence(kb):
    index = OfflineIndexDouble()
    query = "Wi-Fi connection"
    index.upsert([{"id": "BAD:1", "values": kb.embeddings.encode([query])[0],
                   "metadata": {"embedding_model": "different-model", "text": "bad"}}], kb.namespace)
    isolated = KnowledgeBase(index=index, embeddings=kb.embeddings)
    assert isolated.search(query)["sources"] == []


def test_embeddings_are_384_dimensional_normalized_and_semantic():
    vectors = MiniLMEmbeddings().encode(["printer stalled job queue", "printer queue stuck", "a mountain lake"])
    assert all(len(v) == 384 for v in vectors)
    assert all(abs(math.sqrt(sum(x*x for x in v))-1) < 1e-5 for v in vectors)
    dot = lambda a,b: sum(x*y for x,y in zip(a,b))
    assert dot(vectors[0], vectors[1]) > dot(vectors[0], vectors[2])


def test_chunking_covers_final_words_with_overlap():
    chunks = list(split_document("## Heading\n" + " ".join(f"word{i}" for i in range(300)), size=80, overlap=10))
    assert "word299" in chunks[-1][1]
    assert all(heading == "Heading" for heading, _ in chunks)

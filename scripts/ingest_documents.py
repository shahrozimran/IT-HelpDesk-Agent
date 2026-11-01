import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import argparse
from src.config import Settings
from src.rag import KnowledgeBase

if __name__ == "__main__":
    settings = Settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true", help="Check resources locally without connecting to Pinecone.")
    args = parser.parse_args()
    knowledge = KnowledgeBase(settings)
    result = ({"state": "prepared_local_only", "documents": knowledge.document_count,
               "prepared_chunks": len(knowledge.records), "store": "Pinecone",
               "uploaded": False} if args.prepare_only else knowledge.ingest())
    print(json.dumps(result, indent=2))
    filename = "preparation.json" if args.prepare_only else "ingestion.json"
    (settings.evidence_dir / filename).write_text(json.dumps(result, indent=2), encoding="utf-8")

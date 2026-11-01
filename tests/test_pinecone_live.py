"""Opt-in cloud integration test; skipped until credentials and opt-in are present."""
import os
import time
import uuid
import pytest
from src.config import Settings
from src.rag import KnowledgeBase


@pytest.mark.skipif(os.getenv("RUN_PINECONE_LIVE_TESTS") != "1",
                    reason="Pinecone cloud integration awaits connection details and explicit test opt-in.")
def test_live_pinecone_upload_and_retrieval():
    settings = Settings()
    settings.pinecone_namespace += "-test-" + uuid.uuid4().hex[:8]
    kb = KnowledgeBase(settings)
    assert kb.configured, "Configure Pinecone in .env first."
    result = kb.ingest()
    assert result["uploaded_chunks"] == len(kb.records)
    sources = []
    for _ in range(15):
        sources = kb.search("Windows 11 Wi-Fi airplane mode Campus-Lab")["sources"]
        if sources:
            break
        time.sleep(1)
    assert sources and sources[0]["source_id"] == "WIFI"

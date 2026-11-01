import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import asyncio
import json
from src.config import Settings
from src.mcp_client import HelpdeskMCP
from src.rag import KnowledgeBase


async def main():
    settings = Settings()
    checks = {"python": sys.version.split()[0], "provider": settings.provider,
        "model_configured": bool(settings.model), "api_key_configured": bool(settings.api_key),
        "pinecone": KnowledgeBase(settings).status()}
    try:
        async with HelpdeskMCP(settings) as client:
            checks["mcp_tools"] = client.tools
            checks["mcp_result"] = await client.call("get_service_status", {"service_name": "wifi"})
    except Exception as exc:
        checks["mcp_error"] = type(exc).__name__
    report = json.dumps(checks, indent=2)
    (settings.evidence_dir / "setup_check.json").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    asyncio.run(main())

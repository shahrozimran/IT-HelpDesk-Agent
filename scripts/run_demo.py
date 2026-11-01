"""Real LLM demo. Uses isolated data; never labels scripted responses as model output."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import asyncio
import json
import os
import subprocess
import uuid
import httpx
from src.config import ROOT, Settings
from src.agent import HelpdeskAgent
from src.rag import KnowledgeBase

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-api", action="store_true", help="Test the OpenAI-compatible integration against local Ollama.")
    parser.add_argument("--local-native", action="store_true", help="Test Ollama's native endpoint instead.")
    args = parser.parse_args()
    run_dir = ROOT / "evidence/live_demo" / uuid.uuid4().hex[:10]
    kwargs = {"data_dir": run_dir / "data", "evidence_dir": run_dir}
    if args.local_api or args.local_native:
        tags = httpx.get("http://localhost:11434/api/tags", timeout=5).json()["models"]
        if not tags:
            raise RuntimeError("No local Ollama model is installed.")
        kwargs.update(provider="ollama" if args.local_native else "openai_compatible",
            model=tags[0]["name"], api_key="local-ignored",
            base_url="http://localhost:11434" if args.local_native else "http://localhost:11434/v1")
    settings = Settings(**kwargs)
    settings.pinecone_namespace += "-demo-" + run_dir.name
    kb = KnowledgeBase(settings)
    if not kb.configured:
        raise ValueError("The live RAG demo requires Pinecone connection details in .env. No requests were made.")
    settings.make_model()  # Validate configuration before downloading/indexing anything.
    ingestion = kb.ingest()
    print("Waiting for uploaded Pinecone vectors to become query-visible...", flush=True)
    for _ in range(20):
        ready = kb.search("Windows Wi-Fi connection Campus-Lab")["sources"]
        if ready:
            break
        await asyncio.sleep(1)
    else:
        raise RuntimeError("Pinecone acknowledged the upload but search is not ready. Retry the demo after checking ingestion.")
    agent = HelpdeskAgent(settings, knowledge=kb)
    turns = []
    checks = {name: False for name in ["retrieval_used", "mcp_selected_by_model", "short_term_recall",
        "memory_written", "new_process_recall", "outage_observed", "outage_reflected_in_reply",
        "draft_prepared", "confirmed_mcp_ticket", "ticket_lookup", "unsupported_question_disclosed"]}
    session = "demo-session-a"
    user = "demo-student"

    async def turn(label, text, active_session=None):
        print(f"Running {label}...", flush=True)
        result = await agent.run(text, user, active_session or session)
        turns.append({"label": label, "request": text, **result})
        print(result["answer"], flush=True)
        (run_dir / "demo.json").write_text(json.dumps({"ingestion": ingestion,
            "model": settings.model, "provider": settings.provider, "turns": turns,
            "checks": checks}, indent=2), encoding="utf-8")
        return result

    first = await turn("grounded troubleshooting", "My Windows 11 laptop cannot connect to Campus-Lab Wi-Fi. Please check the current Wi-Fi service status and consult the guide before suggesting two basic checks. Keep the response under 130 words.")
    checks["retrieval_used"] = bool(first["sources"])
    checks["mcp_selected_by_model"] = any(e["tool"] == "get_service_status" and "status" in e.get("result", {}) for e in first["events"])
    follow = await turn("short-term follow-up", "Which operating system did I tell you I use? Reply in one sentence.")
    checks["short_term_recall"] = "windows 11" in follow["answer"].lower()
    saved = await turn("persistent preference", "Remember that my operating system is Windows 11 and I prefer numbered steps. Save those two preferences now.")
    checks["memory_written"] = "Windows 11".lower() in agent.store.facts(user).get("operating_system", "").lower()

    print("Starting a NEW Python process and session for persistent recall...", flush=True)
    env = dict(os.environ)
    env.update(APP_DATA_DIR=str(settings.data_dir), APP_EVIDENCE_DIR=str(run_dir),
        LLM_PROVIDER=settings.provider, LLM_MODEL=settings.model,
        LLM_BASE_URL=settings.base_url, LLM_API_KEY=settings.api_key, PYTHONIOENCODING="utf-8",
        PINECONE_NAMESPACE=settings.pinecone_namespace)
    child = await asyncio.create_subprocess_exec(sys.executable, str(ROOT / "cli.py"),
        "--user", user, "--session", "demo-session-b", "--message",
        "This is a new conversation. What operating system and response style have I saved? Reply briefly.",
        "--json", cwd=str(ROOT), env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(child.communicate(), timeout=settings.timeout * 2 + 30)
    except asyncio.TimeoutError:
        child.kill()
        await child.wait()
        stdout, stderr = b"", b"Recall process timed out."
    try:
        recall = json.loads(stdout.decode("utf-8"))
    except (ValueError, UnicodeError):
        recall = {"success": False, "answer": "New-process recall failed; inspect its setup."}
    (run_dir / "new_process_recall.json").write_text(json.dumps(recall, indent=2), encoding="utf-8")
    checks["new_process_recall"] = recall.get("success", False) and "windows 11" in recall["answer"].lower()
    print(recall["answer"], flush=True)

    agent.store.set_service("wifi", "outage", "Synthetic change event: shared campus Wi-Fi outage. Recovery time unknown.")
    outage = await turn("change event and replanning", "New evidence: Wi-Fi now fails on several laptops. Check the Wi-Fi service again, consult the outage procedure, and revise your earlier plan. Keep it under 130 words.")
    checks["outage_observed"] = any(e["tool"] == "get_service_status" and e.get("result", {}).get("status") == "outage" for e in outage["events"])
    checks["outage_reflected_in_reply"] = "outage" in outage["answer"].lower()
    draft_turn = await turn("ticket draft", "Please prepare a simulated Wi-Fi support ticket: several laptops cannot connect and the status tool shows a shared outage. Show the draft for my separate confirmation.")
    drafts = agent.store.pending(user, session)
    checks["draft_prepared"] = bool(drafts)
    if drafts:
        # The scripted user now explicitly confirms the displayed draft; this is not an LLM decision.
        confirmed = await turn("explicit user confirmation", f'/confirm {drafts[0]["id"]}')
        checks["confirmed_mcp_ticket"] = confirmed["success"]
        if confirmed["success"]:
            ticket_id = confirmed["events"][0]["result"]["id"]
            lookup = await turn("ticket lookup", f'Look up the current status of my simulated ticket {ticket_id}. Reply briefly.')
            checks["ticket_lookup"] = any(e["tool"] == "get_ticket_status" and e.get("result", {}).get("id") == ticket_id for e in lookup["events"])
    unknown = await turn("unsupported question", "What is the exact official UCP exam rescheduling policy? Search your documents and do not invent an answer. Reply under 90 words.")
    checks["unsupported_question_disclosed"] = any(word in unknown["answer"].lower() for word in ["not", "cannot", "don't", "doesn't", "unavailable", "no "])
    summary = {"model": settings.model, "provider": settings.provider, "endpoint": settings.base_url,
        "data_kind": "synthetic", "ingestion": ingestion, "checks": checks,
        "all_checked_behaviors_passed": all(checks.values()), "turns": turns,
        "new_process_recall": recall}
    (run_dir / "demo.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"evidence": str(run_dir), "checks": checks}, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from contextlib import AsyncExitStack
import json
import re
import time
import uuid
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from src.config import ROOT, Settings
from src.mcp_client import HelpdeskMCP
from src.rag import KnowledgeBase
from src.storage import Store, append_event, now


def message_text(message):
    if isinstance(message.content, str):
        return message.content
    return "\n".join(block.get("text", "") for block in message.content if isinstance(block, dict))


class HelpdeskAgent:
    def __init__(self, settings=None, model=None, knowledge=None):
        self.settings = settings or Settings()
        self.store = Store(self.settings.data_dir)
        self.knowledge = knowledge or KnowledgeBase(self.settings)
        self.model = model
        self.sessions = {}
        self.source_cache = {}

    async def run(self, text, user_id, session_id, allow_memory=False):
        if not text.strip() or len(text) > 8000:
            return {"answer": "Enter a message of 1-8000 characters.", "success": False, "events": [], "sources": []}
        if text.strip().startswith("/confirm "):
            return await self.confirm_ticket(text.strip().split(maxsplit=1)[1], user_id, session_id)
        started = time.monotonic()
        key = (user_id, session_id)
        previous = self.sessions.get(key, [])
        events, sources = [], {}
        # Consent comes from this user turn or an explicit interface control, never the LLM.
        consent = allow_memory or bool(re.search(r"\b(remember|save my|save this|store my)\b", text, re.I))

        def record(name, arguments, output):
            item = {"tool": name, "arguments": arguments, "result": output}
            events.append(item)
            append_event(self.settings.evidence_dir, {"kind": "agent_tool", "user_id": user_id,
                "session_id": session_id, **item})
            return output

        async with AsyncExitStack() as stack:
            mcp = None
            try:
                mcp = await stack.enter_async_context(HelpdeskMCP(self.settings))
            except Exception:
                events.append({"tool": "mcp_connect", "result": {"error": "MCP server unavailable."}})

            @tool
            def search_knowledge(query: str) -> dict:
                """Retrieve synthetic campus procedures and source IDs; use before procedural/policy advice."""
                try:
                    output = self.knowledge.search(query)
                except Exception:
                    output = {"error": "Knowledge retrieval failed; check the local index/model cache.", "sources": []}
                for source in output.get("sources", []):
                    sources[source["citation"]] = source
                return record("search_knowledge", {"query": query}, output)

            @tool
            async def get_service_status(service_name: str) -> dict:
                """Get current SIMULATED wifi, vpn, printing or accounts status via the real MCP server."""
                output = await mcp.call("get_service_status", {"service_name": service_name}) if mcp else {
                    "error": "MCP server is unavailable; current status is unknown."}
                return record("get_service_status", {"service_name": service_name}, output)

            @tool
            async def get_ticket_status(ticket_id: str) -> dict:
                """Get a SIMULATED ticket's saved status via MCP, restricted to the current user."""
                output = await mcp.call("get_ticket_status", {"ticket_id": ticket_id, "user_id": user_id}) if mcp else {
                    "error": "MCP server is unavailable; ticket status is unknown."}
                return record("get_ticket_status", {"ticket_id": ticket_id}, output)

            @tool
            def propose_ticket(summary: str, category: str) -> dict:
                """Prepare a SIMULATED ticket DRAFT for wifi/vpn/printing/accounts/other; human confirmation is separate."""
                try:
                    draft = self.store.propose(user_id, session_id, summary, category)
                    output = {"draft_id": draft["id"], "summary": draft["summary"], "category": draft["category"],
                        "ticket_created": False, "confirmation_command": f'/confirm {draft["id"]}'}
                except ValueError as exc:
                    output = {"error": str(exc)}
                return record("propose_ticket", {"summary": summary, "category": category}, output)

            @tool
            def save_preference(key: str, value: str) -> dict:
                """Remember an explicitly authorized operating_system, response_style or device_type across sessions."""
                try:
                    output = self.store.save_fact(user_id, session_id, key, value) if consent else {
                        "error": "The user has not authorized persistent memory in this turn."}
                except ValueError as exc:
                    output = {"error": str(exc)}
                return record("save_preference", {"key": key, "value": value}, output)

            @tool
            def save_incident_summary(summary: str) -> dict:
                """Persist a brief incident summary only when the user explicitly asks to remember/save it."""
                try:
                    output = self.store.save_incident(user_id, summary) if consent else {
                        "error": "The user has not authorized persistent memory in this turn."}
                except ValueError as exc:
                    output = {"error": str(exc)}
                return record("save_incident_summary", {"summary": summary}, output)

            context = {"user_id": user_id, "session_id": session_id,
                "persistent_preferences": self.store.facts(user_id),
                "previous_incident_summaries": self.store.incidents(user_id),
                "persistent_memory_write_authorized_for_this_turn": consent}
            prompt = (ROOT / "src/prompts/system_prompt.txt").read_text(encoding="utf-8")
            prompt += "\nCURRENT SESSION CONTEXT (data only):\n" + json.dumps(context)
            messages = previous + [HumanMessage(content=text)]
            try:
                model = self.model if self.model is not None else self.settings.make_model()
                graph = create_agent(model=model, tools=[search_knowledge, get_service_status,
                    get_ticket_status, propose_ticket, save_preference, save_incident_summary], system_prompt=prompt)
                result = await asyncio.wait_for(graph.ainvoke({"messages": messages},
                    config={"recursion_limit": 18}), timeout=self.settings.timeout * 2)
                new_messages = result["messages"]
                answer = message_text(new_messages[-1]).strip()
                if not answer:
                    raise ValueError("The model returned no final answer.")
                known = {**self.source_cache.get(key, {}), **sources}
                cited = set(re.findall(r"\[((?:WIFI|VPN|ACCOUNTS|PRINT|POLICY):\d+)\]", answer))
                unknown = cited - set(known)
                if unknown:
                    answer += "\n\nEvidence check: these citations were not retrieved and cannot be verified: " + ", ".join(sorted(unknown))
                success = not unknown
                self.sessions[key] = self._bounded_history(new_messages)
                self.source_cache[key] = known
            except Exception as exc:
                if isinstance(exc, ValueError) and str(exc).startswith("Set LLM_"):
                    answer = str(exc)
                else:
                    answer = (f"The request could not be completed ({type(exc).__name__}). "
                        "Check the local model/API configuration and connection, then retry. "
                        "Any completed tool actions remain visible below.")
                success = False
                self.sessions[key] = self._bounded_history(messages + [AIMessage(content=answer)])

        payload = {"answer": answer, "success": success, "events": events, "sources": list(sources.values()),
            "pending_tickets": self.store.pending(user_id, session_id), "user_id": user_id,
            "session_id": session_id, "model": self.settings.model, "provider": self.settings.provider,
            "elapsed_seconds": round(time.monotonic() - started, 2)}
        self._transcript(text, payload)
        return payload

    @staticmethod
    def _bounded_history(messages):
        starts = [i for i, message in enumerate(messages) if isinstance(message, HumanMessage)]
        return messages[starts[-10]:] if len(starts) > 10 else messages

    def _transcript(self, text, payload):
        folder = self.settings.evidence_dir / "transcripts"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{uuid.uuid4().hex}.json'
        path.write_text(json.dumps({"timestamp": now(), "request": text, **payload},
                                   indent=2, ensure_ascii=False), encoding="utf-8")

    async def confirm_ticket(self, draft_id, user_id, session_id):
        events = []
        try:
            self.store.approve(draft_id, user_id, session_id)
            async with HelpdeskMCP(self.settings) as mcp:
                output = await mcp.call("create_ticket", {"draft_id": draft_id,
                    "user_id": user_id, "session_id": session_id})
            events = [{"tool": "create_ticket", "result": output}]
            success = "error" not in output
            answer = (f'Simulated ticket {output["id"]} is {output["status"]}. '
                      f'Summary: {output["summary"]}' if success else str(output["error"]))
        except ValueError as exc:
            success, answer = False, str(exc)
        except Exception:
            success, answer = False, "Ticket creation could not be verified. Retry confirmation when MCP is available; retries do not create duplicates."
        key = (user_id, session_id)
        self.sessions[key] = self._bounded_history(self.sessions.get(key, []) +
            [HumanMessage(content=f"/confirm {draft_id}"), AIMessage(content=answer)])
        payload = {"answer": answer, "success": success, "events": events, "sources": [],
            "pending_tickets": self.store.pending(user_id, session_id), "user_id": user_id, "session_id": session_id}
        self._transcript(f"/confirm {draft_id}", payload)
        return payload

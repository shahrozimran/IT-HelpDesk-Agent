"""Exercise real LangChain/OpenAI HTTP code across Streamlit-style event loops."""
import asyncio
import json
import httpx
import pytest
from src.agent import HelpdeskAgent


class Guide:
    def search(self, query):
        return {"sources": [{"citation": "WIFI:1", "source_id": "WIFI",
                             "title": "Wi-Fi guide", "text": "Check Wi-Fi and airplane mode."}]}


def install_loop_bound_transport(monkeypatch, fail=False):
    clients = []
    request_count = 0

    def respond(request):
        nonlocal request_count
        request_count += 1
        if fail:
            return httpx.Response(503, json={"error": {"message": "Synthetic provider unavailable"}})
        body = json.loads(request.content)
        last = body["messages"][-1]
        if last["role"] == "tool":
            message = {"role": "assistant", "content": "Check Wi-Fi and airplane mode. [WIFI:1]"}
            finish = "stop"
        elif str(last.get("content", "")).upper() == "HI":
            message, finish = {"role": "assistant", "content": "Hello!"}, "stop"
        else:
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": f"call-{request_count}", "type": "function", "function": {
                    "name": "search_knowledge", "arguments": json.dumps({"query": "Wi-Fi help"})}}]}
            finish = "tool_calls"
        return httpx.Response(200, json={"id": f"completion-{request_count}",
            "object": "chat.completion", "created": 1, "model": "controlled-http-model",
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})

    class LoopBoundClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(respond), **kwargs)
            self.owner_loop = None
            clients.append(self)

        async def send(self, request, **kwargs):
            loop = asyncio.get_running_loop()
            if self.owner_loop is None:
                self.owner_loop = loop
            elif self.owner_loop is not loop:
                raise RuntimeError("Event loop is closed: transport reused by another chat turn")
            return await super().send(request, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", LoopBoundClient)
    return clients


def test_consecutive_chat_turns_use_private_transports_and_close_them(settings, monkeypatch):
    clients = install_loop_bound_transport(monkeypatch)
    settings.provider = "openai_compatible"
    settings.base_url = "https://model.invalid/v1"
    agent = HelpdeskAgent(settings, knowledge=Guide())
    results = [asyncio.run(agent.run(text, "alice", "session")) for text in
               ["why wifi is not working", "HI", "Why campus Wifi is not working"]]
    assert all(result["success"] for result in results)
    assert all(any(e["tool"] == "search_knowledge" for e in results[i]["events"]) for i in (0, 2))
    assert len(clients) == 3
    assert all(client.is_closed for client in clients)
    assert len({id(client.owner_loop) for client in clients}) == 3


def test_failed_provider_request_still_closes_owned_transport(settings, monkeypatch):
    clients = install_loop_bound_transport(monkeypatch, fail=True)
    settings.provider = "openai_compatible"
    settings.base_url = "https://model.invalid/v1"
    agent = HelpdeskAgent(settings, knowledge=Guide())
    result = asyncio.run(agent.run("Why does Wi-Fi fail?", "alice", "session"))
    assert not result["success"]
    assert len(clients) == 1 and clients[0].is_closed
    events = [json.loads(line) for line in (settings.evidence_dir / "tool_calls.jsonl").read_text().splitlines()]
    assert any(event["kind"] == "agent_error" for event in events)

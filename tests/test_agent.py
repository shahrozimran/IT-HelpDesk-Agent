import asyncio
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from src.agent import HelpdeskAgent


class ControlledModel(BaseChatModel):
    responses: list[AIMessage]
    index: int = 0
    seen: list = []

    @property
    def _llm_type(self):
        return "controlled-test-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(messages)
        if self.index >= len(self.responses):
            raise RuntimeError("No controlled response remaining")
        reply = self.responses[self.index]
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=reply)])


class EmptyKnowledge:
    def search(self, query):
        return {"sources": [], "message": "No matching evidence."}


def call(name, args, id_="tool-1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": id_}])


def test_followup_and_new_session_are_separate(settings):
    model = ControlledModel(responses=[AIMessage(content="What error appears?"),
        AIMessage(content="You previously said Windows 11."), AIMessage(content="New conversation.")])
    agent = HelpdeskAgent(settings, model=model, knowledge=EmptyKnowledge())
    async def check():
        assert (await agent.run("My OS is Windows 11", "alice", "s1"))["success"]
        await agent.run("What OS did I mention?", "alice", "s1")
        assert any(getattr(m, "content", "") == "My OS is Windows 11" for m in model.seen[1])
        await agent.run("Hello", "alice", "s2")
        assert not any(getattr(m, "content", "") == "My OS is Windows 11" for m in model.seen[2])
    asyncio.run(check())


def test_model_cannot_persist_without_user_permission(settings):
    model = ControlledModel(responses=[call("save_preference", {"key": "operating_system", "value": "Windows 11"}),
        AIMessage(content="I cannot save that without permission.")])
    agent = HelpdeskAgent(settings, model=model, knowledge=EmptyKnowledge())
    result = asyncio.run(agent.run("My laptop has a connection problem", "alice", "s1"))
    assert "error" in result["events"][0]["result"]
    assert agent.store.facts("alice") == {}


def test_explicit_memory_and_real_mcp_tool_selection(settings):
    model = ControlledModel(responses=[call("save_preference", {"key": "operating_system", "value": "Windows 11"}),
        call("get_service_status", {"service_name": "wifi"}, "tool-2"),
        AIMessage(content="Saved your preference. The simulated Wi-Fi service is operational.")])
    agent = HelpdeskAgent(settings, model=model, knowledge=EmptyKnowledge())
    result = asyncio.run(agent.run("Remember Windows 11 and check Wi-Fi status", "alice", "s1"))
    assert result["success"]
    assert agent.store.facts("alice")["operating_system"] == "Windows 11"
    assert result["events"][1]["result"]["status"] == "operational"


def test_model_cannot_create_ticket_without_application_confirmation(settings):
    model = ControlledModel(responses=[call("propose_ticket", {"summary": "Wi-Fi unavailable", "category": "wifi"}),
        AIMessage(content="Please confirm the draft.")])
    agent = HelpdeskAgent(settings, model=model, knowledge=EmptyKnowledge())
    async def check():
        result = await agent.run("Open a support ticket", "alice", "s1")
        draft = result["pending_tickets"][0]
        with agent.store.db() as db:
            assert db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 0
        assert not (await agent.confirm_ticket(draft["id"], "alice", "s2"))["success"]
        confirmed = await agent.confirm_ticket(draft["id"], "alice", "s1")
        assert confirmed["success"]
        assert confirmed["events"][0]["result"]["status"] == "open"
    asyncio.run(check())


def test_unknown_citations_are_flagged(settings):
    agent = HelpdeskAgent(settings, model=ControlledModel(responses=[AIMessage(content="Invented [WIFI:99]")]),
                          knowledge=EmptyKnowledge())
    result = asyncio.run(agent.run("Give me a policy", "alice", "s1"))
    assert result["success"] is False
    assert "cannot be verified" in result["answer"]


def test_model_failure_is_explicit(settings):
    agent = HelpdeskAgent(settings, model=ControlledModel(responses=[]), knowledge=EmptyKnowledge())
    result = asyncio.run(agent.run("Hello", "alice", "s1"))
    assert result["success"] is False
    assert "could not be completed" in result["answer"]

import asyncio
import json
from src.mcp_client import HelpdeskMCP
from src.storage import Store


def test_real_stdio_discovery_and_ticket_round_trip(settings):
    async def check():
        store = Store(settings.data_dir)
        draft = store.propose("alice", "s1", "VPN unavailable after permitted checks", "vpn")
        async with HelpdeskMCP(settings) as client:
            assert set(client.tools) == {"get_service_status", "create_ticket", "get_ticket_status"}
            status = await client.call("get_service_status", {"service_name": "wifi"})
            assert status["simulated"] is True
            assert status["status"] == "operational"
            denied = await client.call("create_ticket", {"draft_id": draft["id"], "user_id": "alice", "session_id": "s1"})
            assert "error" in denied
            store.approve(draft["id"], "alice", "s1")
            args = {"draft_id": draft["id"], "user_id": "alice", "session_id": "s1"}
            ticket = await client.call("create_ticket", args)
            assert ticket["status"] == "open"
            assert (await client.call("create_ticket", args))["id"] == ticket["id"]
            assert (await client.call("get_ticket_status", {"ticket_id": ticket["id"], "user_id": "alice"}))["id"] == ticket["id"]
            assert "error" in await client.call("get_ticket_status", {"ticket_id": ticket["id"], "user_id": "bob"})
            assert "error" in await client.call("missing_tool", {})
        lines = [json.loads(line) for line in (settings.evidence_dir / "tool_calls.jsonl").read_text().splitlines()]
        assert any(line["kind"] == "mcp_initialize" for line in lines)
        assert any(line.get("tool") == "create_ticket" for line in lines)
    asyncio.run(check())

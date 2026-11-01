from contextlib import AsyncExitStack
from datetime import timedelta
import json
import os
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.config import ROOT
from src.storage import append_event


class HelpdeskMCP:
    def __init__(self, settings):
        self.settings = settings
        self.stack = AsyncExitStack()
        self.session = None
        self.tools = []

    async def __aenter__(self):
        env = dict(os.environ)
        env["APP_DATA_DIR"] = str(self.settings.data_dir)
        env["APP_EVIDENCE_DIR"] = str(self.settings.evidence_dir)
        try:
            read, write = await self.stack.enter_async_context(stdio_client(StdioServerParameters(
                command=sys.executable, args=[str(ROOT / "mcp_server/server.py")],
                cwd=str(ROOT), env=env)))
            self.session = await self.stack.enter_async_context(
                ClientSession(read, write, read_timeout_seconds=timedelta(seconds=20)))
            init = await self.session.initialize()
            discovered = await self.session.list_tools()
            self.tools = [tool.name for tool in discovered.tools]
            append_event(self.settings.evidence_dir, {"kind": "mcp_initialize", "transport": "stdio",
                "server": init.serverInfo.name, "protocol": init.protocolVersion, "tools": self.tools})
            return self
        except BaseException:
            await self.stack.aclose()
            raise

    async def __aexit__(self, *args):
        return await self.stack.__aexit__(*args)

    async def call(self, name, arguments):
        if name not in self.tools:
            return {"error": f"MCP server did not expose {name}."}
        start = time.monotonic()
        try:
            result = await self.session.call_tool(name, arguments)
            texts = [c.text for c in result.content if c.type == "text"]
            output = json.loads(texts[0]) if len(texts) == 1 else {"content": texts}
            if result.isError:
                output = {"error": output}
        except Exception as exc:
            output = {"error": f"MCP call failed ({type(exc).__name__}). Retry when the tool is available."}
        append_event(self.settings.evidence_dir, {"kind": "mcp_call", "tool": name,
            "arguments": arguments, "result": output, "elapsed_seconds": round(time.monotonic() - start, 3)})
        return output

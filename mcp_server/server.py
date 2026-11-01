"""Run as a child process. stdout is exclusively the MCP protocol."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import Settings
from src.storage import Store
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Synthetic University Helpdesk")
store = Store(Settings().data_dir)


@mcp.tool()
def get_service_status(service_name: str) -> dict:
    """Read current SIMULATED wifi, vpn, printing or accounts status."""
    return store.service(service_name)


@mcp.tool()
def create_ticket(draft_id: str, user_id: str, session_id: str) -> dict:
    """Create a SIMULATED ticket from an already human-approved draft; retries are idempotent."""
    return store.create_ticket(draft_id, user_id, session_id)


@mcp.tool()
def get_ticket_status(ticket_id: str, user_id: str) -> dict:
    """Read a SIMULATED ticket belonging to the selected user."""
    return store.ticket(ticket_id, user_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")

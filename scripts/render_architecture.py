"""Generate a portable vector diagram with the Python standard library."""
from pathlib import Path
from html import escape

root = Path(__file__).resolve().parents[1]
nodes = [
    ("prompt", 30, 60, "SYSTEM PROMPT", ["Role · evidence · memory", "tool rules · uncertainty"]),
    ("user", 500, 60, "USER INTERFACE", ["Local chat UI or CLI", "Explicit ticket confirmation"]),
    ("model", 980, 60, "CONFIGURED LLM", ["Interprets the request", "Selects tools and writes reply"]),
    ("session", 30, 235, "SHORT-TERM MEMORY", ["Recent conversation messages", "Scoped by user + session"]),
    ("agent", 500, 235, "ONE PYTHON AI AGENT", ["LangChain tool-calling loop", "Grounded reply + citations"]),
    ("rag", 980, 235, "RAG RETRIEVAL TOOL", ["Semantic document search", "Source IDs + passages"]),
    ("memory", 30, 420, "LONG-TERM MEMORY", ["SQLite preferences + incidents", "Retrieved in a new session"]),
    ("client", 500, 420, "PYTHON MCP CLIENT", ["Initializes + discovers tools", "Invokes real tool calls"]),
    ("index", 980, 420, "PINECONE (REMOTE)", ["384-dimensional cosine vectors", "Local MiniLM embeddings + metadata"]),
    ("evidence", 30, 615, "EXECUTION EVIDENCE", ["Tool requests and real results", "Transcripts + test outcomes"]),
    ("server", 500, 615, "SEPARATE MCP SERVER", ["Official SDK / FastMCP", "Services + confirmed tickets"]),
    ("state", 980, 615, "SIMULATED SERVICE STATE", ["SQLite service status + tickets", "Approval and duplicate checks"]),
]
parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="840" viewBox="0 0 1360 840">',
    '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#648194"/></marker></defs>',
    '<rect width="1360" height="840" fill="#f5f7fb"/>',
    '<text x="30" y="30" font-family="Arial,sans-serif" font-size="22" font-weight="bold" fill="#10263b">Campus Helpdesk · Scenario 23</text>']


def line(path, two=False):
    parts.append(f'<path d="{path}" fill="none" stroke="#648194" stroke-width="2.5" marker-end="url(#arrow)"' +
                 (' marker-start="url(#arrow)"' if two else '') + '/>')


for path, two in [
    ("M340 110H420V260H500", False), ("M655 160V235", True),
    ("M980 110H900V260H810", True), ("M340 285H500", True),
    ("M340 470H420V315H500", True), ("M810 285H980", True),
    ("M1135 335V420", True), ("M655 335V420", True),
    ("M655 520V615", True), ("M810 665H980", True),
    ("M500 310H385V665H340", False),
]:
    line(path, two)
parts.append('<text x="676" y="572" font-family="Arial,sans-serif" font-size="18" fill="#087e8b">stdio protocol</text>')
for id_, x, y, title, lines in nodes:
    active = id_ == "agent"
    fill, title_color, body_color = ("#087e8b", "white", "#e8ffff") if active else ("white", "#10263b", "#486277")
    parts.append(f'<rect x="{x}" y="{y}" width="310" height="100" rx="12" fill="{fill}" stroke="#cfdae4"/>')
    parts.append(f'<text x="{x+16}" y="{y+27}" font-family="Arial,sans-serif" font-size="17" font-weight="bold" fill="{title_color}">{escape(title)}</text>')
    for i, text in enumerate(lines):
        parts.append(f'<text x="{x+16}" y="{y+54+i*23}" font-family="Arial,sans-serif" font-size="15" fill="{body_color}">{escape(text)}</text>')
parts += ['<text x="30" y="778" font-family="Arial,sans-serif" font-size="17" fill="#486277">All campus policies, services and tickets are synthetic educational data.</text>',
    '<text x="30" y="807" font-family="Arial,sans-serif" font-size="15" fill="#648194">One primary AI agent. RAG knowledge and persistent user memory have distinct purposes.</text>', '</svg>']
(root / "docs/architecture.svg").write_text("\n".join(parts), encoding="utf-8")
print("Created docs/architecture.svg")

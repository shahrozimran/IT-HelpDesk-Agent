"""Package source, docs and selected verification evidence; exclude secrets and caches."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
output = root / "output"
output.mkdir(exist_ok=True)
selected = []
for relative in ["README.md", "IMPLEMENTATION_PLAN.md", "requirements.txt", "requirements.in",
    ".env.example", ".gitignore", "pytest.ini", "cli.py", "app.py", "setup.ps1", "run.ps1",
    ".streamlit/config.toml", "data/source_manifest.json", "evidence/ingestion.json", "evidence/preparation.json",
    "evidence/test_results.txt", "evidence/verification.md", "evidence/api_smoke.json",
    "evidence/setup_check.json", "evidence/ui_browser_check.json", "evidence/screenshots/chat.jpg", "evidence/screenshots/knowledge.jpg",
    "evidence/pinecone_connection.json", "evidence/openrouter_connection.json",
    "evidence/screenshots/pinecone_index.jpg"]:
    path = root / relative
    if path.is_file():
        selected.append(path)
for directory in ["src", "mcp_server", "scripts", "data/knowledge", "docs", "tests"]:
    selected += [p for p in (root / directory).rglob("*") if p.is_file()
                 and "__pycache__" not in p.parts and p.suffix != ".pyc"]
live = sorted((root / "evidence/live_demo").glob("*/demo.json"), key=lambda p: p.stat().st_mtime)
if live:
    selected.append(live[-1])
archive = output / "Assignment_2_Helpdesk_Source.zip"
secrets = dotenv_values(root / ".env")
for path in set(selected):
    payload = path.read_bytes()
    for name in ("LLM_API_KEY", "PINECONE_API_KEY"):
        value = secrets.get(name)
        if value and value.encode() in payload:
            raise ValueError(f"Refusing to package a file containing a configured credential: {path.name}")
with ZipFile(archive, "w", compression=ZIP_DEFLATED) as z:
    for path in sorted(set(selected)):
        z.write(path, Path("Solution") / path.relative_to(root))
print(f"Created {archive} with {len(set(selected))} files. No .env, databases or caches included.")

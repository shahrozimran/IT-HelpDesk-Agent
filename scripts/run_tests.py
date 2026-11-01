"""Record a complete test result only after the pytest process finishes."""
from pathlib import Path
import subprocess
import sys
import os
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=root,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
report = result.stdout + result.stderr
values = dotenv_values(root / ".env")
for name in ("LLM_API_KEY", "PINECONE_API_KEY"):
    for secret in (values.get(name), os.getenv(name)):
        if secret:
            report = report.replace(secret, "[REDACTED]")
pending = root / "evidence/test_results.pending.txt"
pending.write_text(report, encoding="utf-8")
pending.replace(root / "evidence/test_results.txt")
print(report, end="")
raise SystemExit(result.returncode)

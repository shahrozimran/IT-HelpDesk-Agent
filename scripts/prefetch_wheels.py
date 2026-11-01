"""Optional resumable downloader for large Windows CPython 3.12 dependencies."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import urllib.request

root = Path(__file__).resolve().parents[1]
cache = root / ".cache/wheels"
cache.mkdir(parents=True, exist_ok=True)
for package, version in [("onnxruntime", "1.31.1"), ("pandas", "3.1.0"),
                         ("pillow", "13.0.0"), ("pyarrow", "26.0.0"), ("pydeck", "0.9.3")]:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/{version}/json", timeout=30) as response:
        metadata = json.load(response)
    candidates = [f for f in metadata["urls"] if "cp312" in f["filename"] and "win_amd64" in f["filename"]]
    if not candidates:
        candidates = [f for f in metadata["urls"] if f["filename"].endswith("none-any.whl")]
    item = candidates[0]
    target = cache / item["filename"]
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == item["digests"]["sha256"]:
        continue
    parts = cache / (package + "-parts")
    parts.mkdir(exist_ok=True)
    size, total = 1024 * 1024, item["size"]

    def fetch(start):
        end = min(start + size, total) - 1
        part = parts / str(start)
        if not part.exists() or part.stat().st_size != end - start + 1:
            request = urllib.request.Request(item["url"], headers={"Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 206:
                    raise ValueError("Range response required")
                data = response.read()
            if len(data) != end - start + 1:
                raise ValueError("Incomplete wheel range")
            part.write_bytes(data)
        return part

    with ThreadPoolExecutor(max_workers=6) as pool:
        ordered = list(pool.map(fetch, range(0, total, size)))
    partial = target.with_suffix(".part")
    with partial.open("wb") as stream:
        for part in ordered:
            stream.write(part.read_bytes())
    if hashlib.sha256(partial.read_bytes()).hexdigest() != item["digests"]["sha256"]:
        raise ValueError("Wheel checksum mismatch")
    partial.replace(target)
    print("Verified", target.name, flush=True)

"""Prefetch the checksum-verified public MiniLM ONNX archive; no vector store is used."""
from pathlib import Path
import hashlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor

root = Path(__file__).resolve().parents[1]
folder = root / ".cache/models/onnx"
folder.mkdir(parents=True, exist_ok=True)
archive = folder / "onnx.tar.gz"
expected = "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"
if archive.exists() and hashlib.file_digest(archive.open("rb"), "sha256").hexdigest() == expected:
    print("Embedding archive already verified.")
else:
    url = "https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz"
    # Small resumable ranges avoid stalled large-object transfers on this connection.
    total = 83178821
    size = 2 * 1024 * 1024
    parts = folder / "parts"
    parts.mkdir(exist_ok=True)

    def fetch(start):
        end = min(start + size, total) - 1
        part = parts / str(start)
        if part.exists() and part.stat().st_size == end - start + 1:
            return part
        request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 206:
                raise ValueError("Server did not honor the requested model range.")
            data = response.read()
        if len(data) != end - start + 1:
            raise ValueError("Incomplete model range; rerun to resume.")
        part.write_bytes(data)
        print(f"Downloaded bytes {start}-{end}", flush=True)
        return part

    with ThreadPoolExecutor(max_workers=6) as pool:
        ordered = list(pool.map(fetch, range(0, total, size)))
    temporary = archive.with_suffix(".gz.assembled")
    with temporary.open("wb") as out:
        for part in ordered:
            out.write(part.read_bytes())
    with temporary.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError("Embedding archive checksum mismatch; the file will not be used.")
    temporary.replace(archive)
    print("Downloaded and SHA-256 verified:", archive)

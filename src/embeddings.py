"""Local MiniLM inference, independent of the remote vector database."""
from src.config import ROOT
import hashlib
import runpy
import tarfile


class MiniLMEmbeddings:
    model_name = "all-MiniLM-L6-v2-onnx-384"
    dimension = 384

    def __init__(self):
        self._session = None
        self._tokenizer = None

    def _load(self):
        if self._session is not None:
            return
        import onnxruntime as ort
        from tokenizers import Tokenizer
        cache = ROOT / ".cache/models/onnx"
        folder = cache / "onnx"
        if not (folder / "model.onnx").exists():
            runpy.run_path(str(ROOT / "scripts/download_embeddings.py"), run_name="__main__")
            archive = cache / "onnx.tar.gz"
            with archive.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3":
                raise ValueError("Embedding model archive failed integrity verification.")
            with tarfile.open(archive, "r:gz") as stream:
                stream.extractall(cache, filter="data")
        self._tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self._tokenizer.enable_truncation(max_length=256)
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self._session = ort.InferenceSession(str(folder / "model.onnx"), sess_options=options,
                                            providers=["CPUExecutionProvider"])

    def encode(self, texts):
        if not texts:
            return []
        import numpy as np
        self._load()
        encoded = self._tokenizer.encode_batch(texts)
        data = {
            "input_ids": np.asarray([e.ids for e in encoded], dtype=np.int64),
            "attention_mask": np.asarray([e.attention_mask for e in encoded], dtype=np.int64),
            "token_type_ids": np.asarray([e.type_ids for e in encoded], dtype=np.int64),
        }
        names = {entry.name for entry in self._session.get_inputs()}
        hidden = self._session.run(None, {k: v for k, v in data.items() if k in names})[0]
        mask = data["attention_mask"][:, :, None].astype(np.float32)
        pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1e-9)
        normalized = pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
        return normalized.astype(np.float32).tolist()

from dataclasses import dataclass, field
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]

# Set these before importing packages that download models or create caches.
for name, relative in {
    "HF_HOME": ".cache/models/huggingface",
    "XDG_CACHE_HOME": ".cache",
    "PIP_CACHE_DIR": ".cache/pip",
    "TMP": "tmp/runtime",
    "TEMP": "tmp/runtime",
    "MPLCONFIGDIR": ".cache/matplotlib",
}.items():
    path = ROOT / relative
    path.mkdir(parents=True, exist_ok=True)
    os.environ[name] = str(path)
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)


def local_path(value: str | Path) -> Path:
    path = Path(value)
    path = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Project data and evidence paths must stay inside Solution.")
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Settings:
    data_dir: Path | None = None
    evidence_dir: Path | None = None
    provider: str = ""
    model: str = ""
    base_url: str = ""
    api_key: str = field(default="", repr=False)
    timeout: float = 180.0
    pinecone_api_key: str = field(default="", repr=False)
    pinecone_host: str = ""
    pinecone_namespace: str = ""

    def __post_init__(self):
        self.data_dir = local_path(self.data_dir or os.getenv("APP_DATA_DIR", "data"))
        self.evidence_dir = local_path(self.evidence_dir or os.getenv("APP_EVIDENCE_DIR", "evidence"))
        self.provider = self.provider or os.getenv("LLM_PROVIDER", "openai_compatible")
        self.model = self.model or os.getenv("LLM_MODEL", "")
        self.base_url = self.base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.api_key = self.api_key or os.getenv("LLM_API_KEY", "")
        self.timeout = float(os.getenv("LLM_TIMEOUT", str(self.timeout)))
        self.pinecone_api_key = self.pinecone_api_key or os.getenv("PINECONE_API_KEY", "")
        self.pinecone_host = self.pinecone_host or os.getenv("PINECONE_INDEX_HOST", "")
        self.pinecone_namespace = self.pinecone_namespace or os.getenv("PINECONE_NAMESPACE", "abm-assignment2")

    def make_model(self):
        if not self.model:
            raise ValueError("Set LLM_MODEL in Solution/.env to a model supporting tool calling.")
        if self.provider == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(model=self.model, base_url=self.base_url,
                              temperature=0, num_ctx=8192, num_predict=1200,
                              reasoning=False, client_kwargs={"timeout": self.timeout})
        if self.provider != "openai_compatible":
            raise ValueError("LLM_PROVIDER must be openai_compatible or ollama.")
        if not self.api_key:
            raise ValueError("Set LLM_API_KEY in Solution/.env. Use a dummy value only for a local endpoint.")
        from langchain_openai import ChatOpenAI
        from urllib.parse import urlparse
        # Ollama's compatible endpoint accepts a dummy key and an explicit no-thinking
        # control. Do not send this provider-specific setting to remote APIs.
        local_extra = {"reasoning_effort": "none"} if urlparse(self.base_url).hostname in {
            "localhost", "127.0.0.1"} else {}
        return ChatOpenAI(model=self.model, base_url=self.base_url, api_key=self.api_key,
                          temperature=0, timeout=self.timeout, max_retries=0,
                          max_tokens=1200, extra_body=local_extra)

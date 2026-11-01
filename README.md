# IT-HelpDesk-Agent

Campus Helpdesk - Assignment 2, scenario 23.

One Python LLM agent with session memory, persistent user/task memory, Pinecone RAG over five resources, and a real local MCP client-server interaction. Every campus policy, service and ticket is **synthetic educational data**, not official UCP information. Pinecone is the selected vector database; user preferences, incident summaries and simulated tickets remain in SQLite.

The current local installation is configured for **Claude Sonnet 4.6 through OpenRouter** and Pinecone index **abm-helpdesk**. Twenty document passages have been uploaded to the main namespace. The live demo passed all eleven checks; see `evidence/verification.md`. Local credentials are already saved in `.env`; the template contains no keys.

The GitHub repository contains source code, synthetic knowledge resources, documentation, tests and curated verification summaries. Each clone needs its own `.env` configured from `.env.example`. API keys, local databases, model caches, runtime transcripts, screenshots and generated archives are excluded. Detailed live execution artifacts referenced in the report remain in the original local Solution folder.

## Start on this computer

All commands run from `D:\Desktop\UCP\7th semester\Agent Based Modeling\Assignments\Assignment 2\Solution`.

1. Configure `.env`: set `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` to your chosen provider. Set `PINECONE_API_KEY` and `PINECONE_INDEX_HOST` when you have those details. Use a model that supports Chat Completions function/tool calls. Keep secrets in this local file.
2. Start the local interface:

```powershell
.\run.ps1
```

Open http://127.0.0.1:8501. Restart the app after changing `.env`. The local guides remain readable before configuration. LLM chat requires your model settings, and grounded document retrieval requires a connected Pinecone index with uploaded passages. Missing connections are shown as pending; no local vector database fallback is used.

CLI alternative:

```powershell
.\.venv\Scripts\python.exe cli.py --user student
```

Commands: `/new` begins an empty conversation; `/memory` shows saved facts; `/confirm D-id` confirms a displayed draft; `/quit` exits. Session history stays in process memory, while saved preferences, incident summaries and tickets survive a restart.

## Recreate the environment

Use Python 3.12. The project on this computer uses a local `.venv` created with the available bundled Python 3.12 runtime. A standard Python 3.12 installation is sufficient on another Windows computer.

```powershell
.\setup.ps1
```

The setup script installs `requirements.txt`, creates `.env` only if missing, and prepares the resources. It uploads vectors only when Pinecone connection settings are present. The first embedding run downloads a checksum-verified public all-MiniLM-L6-v2 ONNX model (~80 MB) into `.cache/models/onnx`. Embeddings are generated locally; vector storage and similarity search run in Pinecone and require network access.

## Pinecone configuration

Connect a **vector-based dense index with 384 dimensions and cosine similarity**, suitable for bringing your own vectors. This adapter uses Pinecone's vector `upsert` and `query` methods, rather than document-schema or integrated-embedding methods. If an existing index has different settings, provide its details before ingestion so the adapter/model can be adjusted.

Set these values in `.env` when available:

```dotenv
PINECONE_API_KEY=
PINECONE_INDEX_HOST=
PINECONE_NAMESPACE=abm-assignment2
```

The index host comes from your Pinecone index connection details. The application does not automatically create a cloud index. Resource/model fingerprints are appended to the namespace, keeping changed corpora separate without deleting unrelated vectors. Repeated ingestion of the same corpus uses stable IDs. Pinecone is eventually consistent: allow time after a successful upsert before querying.

After editing knowledge files, rerun ingestion and restart the app so its corpus namespace refreshes.

```powershell
.\.venv\Scripts\python.exe scripts/ingest_documents.py --prepare-only
# After supplying Pinecone settings:
.\.venv\Scripts\python.exe scripts/ingest_documents.py
```

`--prepare-only` checks the five local resources and records preparation evidence; it does not upload or claim remote retrieval was verified.

If PowerShell script execution is restricted, use the equivalent commands directly:

```powershell
py -3.12 -m venv .venv
$env:PIP_CACHE_DIR = "$PWD\.cache\pip"
$env:TEMP = "$PWD\tmp\install"
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env  # only when .env does not already exist
.\.venv\Scripts\python.exe scripts/ingest_documents.py --prepare-only
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

## Verify and demonstrate

```powershell
.\.venv\Scripts\python.exe scripts/check_setup.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/run_tests.py  # also saves evidence/test_results.txt
.\.venv\Scripts\python.exe scripts/run_demo.py
```

The demo requires both Pinecone and LLM settings. It uses isolated local data and a dedicated Pinecone namespace, makes real requests and can incur provider charges. Its JSON records actual outputs and checks, including a new Python process for long-term recall. Offline tests use explicitly identified Pinecone test doubles and controlled models; these do not establish cloud connectivity.

To opt into the real Pinecone upload/retrieval test after configuring the connection:

```powershell
$env:RUN_PINECONE_LIVE_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests/test_pinecone_live.py -q
Remove-Item Env:RUN_PINECONE_LIVE_TESTS
```

If local Ollama is installed, `scripts/run_demo.py --local-api` tests the same OpenAI-compatible integration against its local endpoint, using an installed model. `--local-native` tests the optional native Ollama adapter. Neither command changes `.env` or downloads a chat model. Local inference can be slow depending on hardware. The default application remains configured for your chosen API.

Manual replanning demo, in a separate terminal:

```powershell
.\.venv\Scripts\python.exe scripts/set_service.py wifi outage --detail "Shared simulated outage; recovery time unknown."
```

Ask the assistant to check service status again and revise its plan. Restore afterward:

```powershell
.\.venv\Scripts\python.exe scripts/set_service.py wifi operational --detail "Synthetic service restored."
```

## Submission and evidence

- `docs/report.md`: scenario, environment, implementation, prompt justification and limitations.
- `docs/architecture.md`: component diagram and request/data flow.
- `docs/demo_script.md`: marking walkthrough.
- `data/source_manifest.json`: five distinct resources with provenance.
- `src/prompts/system_prompt.txt`: actual system prompt.
- `evidence/preparation.json`: local resource preparation, explicitly not a cloud upload.
- `evidence/ingestion.json`, `evidence/test_results.txt`, `evidence/verification.md`: actual ingestion and verification results when generated.
- `evidence/tool_calls.jsonl` and `evidence/transcripts/`: real observable tool actions and turn records.

Review any evidence before sharing. Local transcripts retain chat text for assessment. Do not enter passwords or private information. The demo user selector illustrates isolation but is not real authentication. The application is intended for local assignment use.

The instructor's separate scenario pack was not supplied. Synthetic fixtures must be reconciled with its required evidence, constraints, alternatives and change event before final submission. Add your name and registration number to the report.

`requirements.in` declares direct dependency ranges; `requirements.txt` records the tested installation. Keep source, knowledge, docs and selected evidence for submission; exclude `.env`, `.venv`, caches and unnecessary temporary files. All project working files stay in `Solution`; the selected Pinecone database will hold vectors remotely after configuration.

## Troubleshooting

- **Model/key missing:** edit `.env`, then restart the app. The application never fabricates an LLM response when configuration is absent.
- **HTTP authentication/not-found/tool errors:** check provider URL, model ID, account access and Chat Completions tool support. A Responses-only model is not compatible with this adapter.
- **Pinecone pending:** enter the index host and key in `.env`, confirm 384 dimensions/cosine, then run ingestion.
- **Empty retrieval:** inspect actual ingestion evidence and namespace; allow time for Pinecone query visibility after upserts.
- **Embedding download fails:** retry `scripts/download_embeddings.py`. The public archive host distributes model files only; it is not a vector database dependency. Changing the embedding model requires a compatible index and reingestion.
- **MCP unavailable:** run `scripts/check_setup.py` with the project interpreter. The client launches `mcp_server/server.py` itself; no separate port or manual server startup is needed.
- **Timeout:** choose a responsive model or adjust `LLM_TIMEOUT`. Inspect the turn's completed actions before retrying a write. Ticket confirmation is idempotent.

## References

[LangChain agents](https://docs.langchain.com/oss/python/langchain/agents), [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), [MCP Python SDK v1](https://py.sdk.modelcontextprotocol.io/v1/), [Pinecone vector operations](https://sdk.pinecone.io/python/how-to/vectors/upsert-and-query.html), [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility).

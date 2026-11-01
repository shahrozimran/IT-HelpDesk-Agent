# Verification record - 1 November 2026

Scenario: **23, IT Helpdesk Troubleshooting Agent**. All project working files are in the specified Solution folder.

## Configured services

- LLM: **anthropic/claude-sonnet-4.6 through OpenRouter**.
- Vector database: **Pinecone**, index **abm-helpdesk**, AWS us-east-1, 384 dimensions, cosine metric.
- Main knowledge namespace: **abm-assignment2-9e055637723f**.
- Five knowledge resources and **20 passages** were actually uploaded to the main namespace.
- API keys are saved only in the excluded local configuration file. The source packager checks selected files for configured key values before creating the ZIP.

## Observed results

| Check | Actual result | Evidence |
| --- | --- | --- |
| Automated suite including opted-in Pinecone cloud test | **32 passed in 37.00 seconds; none skipped** | test_results.txt |
| OpenRouter connection and selected model | Real model returned the verification reply | openrouter_connection.json |
| Pinecone creation/configuration | Index ready; 384 dimensions/cosine confirmed through API and browser | pinecone_connection.json; screenshots/pinecone_index.jpg |
| Main ingestion | Five documents, 20 upsert acknowledgements | ingestion.json |
| Main namespace readiness | Connected; 20 indexed passages | setup_check.json |
| Cloud vector retrieval | Actual upload and relevant query passed in a separate test namespace | ../tests/test_pinecone_live.py |
| Embeddings and adapter contracts | Actual normalized embeddings; source relevance, filters, namespaces and SDK response types passed | ../tests/test_rag.py |
| Persistent memory | Saved facts survived a new Python process; user isolation passed | Storage tests and live demo |
| MCP | Real child-process stdio discovery, status calls and ticket operations passed | setup_check.json and MCP tests |
| Ticket oversight | Confirmation, owner/session checks and idempotency passed | Storage, agent and MCP tests |
| Credential handling | Settings representation hides keys; test logs redact configured keys | ../tests/test_config.py; ../scripts/run_tests.py |
| App | AppTest passed; browser showed no configuration warnings and displayed 20 Pinecone passages | ui_browser_check.json; screenshots/chat.jpg; screenshots/knowledge.jpg |

## Live agent demonstration

The real Claude/OpenRouter + Pinecone + MCP demonstration passed **all 11 checks**. Full model responses, user prompts, actual tool arguments/results and retrieved passages are recorded in:

live_demo/465a8d8c36/demo.json

Verified behaviors:

1. Source retrieval from Pinecone.
2. MCP service-status tool selected by the LLM.
3. Short-term conversational recall.
4. Persistent preference write.
5. Recall in a separate Python process and session.
6. Fresh outage observation through MCP.
7. Reply revised to reflect the outage.
8. Ticket draft prepared without creating a ticket.
9. Actual MCP creation after the scripted user explicitly confirms.
10. Saved ticket status retrieved through MCP.
11. Unsupported official-policy question answered with disclosure of missing evidence.

The live demo and cloud tests use separate namespaces and local data directories. The main app retains its own 20-passage namespace. Additional records visible in the Pinecone index belong to these verification namespaces.

## Reproduce

Ordinary checks keep the cloud test opt-in. To repeat the fully enabled suite:

    $env:RUN_PINECONE_LIVE_TESTS='1'
    .\.venv\Scripts\python.exe scripts/run_tests.py
    Remove-Item Env:RUN_PINECONE_LIVE_TESTS

Connection and live demo commands:

    .\.venv\Scripts\python.exe scripts/check_setup.py
    .\.venv\Scripts\python.exe scripts/run_demo.py

The demonstration makes actual model/API calls. Its prompts, explicit user confirmation and outputs remain inspectable.

## Remaining submission context

The instructor's separate scenario pack has not been supplied. Knowledge guides and the outage fixture are labeled synthetic; reconcile them with that pack before assessment. Student name and registration number still need to be added to the report.

Pinecone is the active vector backend. SQLite handles preferences, incident summaries and simulated operations. The earlier backend and its evidence are archived locally and excluded from the source package.

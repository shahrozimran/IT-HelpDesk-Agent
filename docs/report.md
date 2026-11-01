# Assignment 2: Scenario-Based Intelligent Agent Analysis

**Course:** Agent Based Modeling (AIDE3313)

**Institution:** University of Central Punjab

**Scenario:** 23 - IT Helpdesk Troubleshooting Agent

**Student name:** To be completed by student

**Registration number:** To be completed by student

**Current integration status:** The agent is configured with `anthropic/claude-sonnet-4.6` through OpenRouter and the Pinecone index `abm-helpdesk`. Live vector upload/search, actual MCP interactions and all eleven live demonstration checks passed. API keys remain in the excluded local `.env` file.

## 1. Problem and scope

Students and staff may describe an IT issue without knowing whether it comes from their device, their account or a shared service outage. Repeating generic advice wastes time and ignores previous attempts. The Campus Helpdesk prototype combines documented procedures, current simulated service observations and remembered context to suggest grounded next steps.

The project implements one primary Python AI agent connected to a configurable tool-calling LLM. It supports Wi-Fi, VPN, printing, account-access guidance and simulated ticket management. All policies and operational records are synthetic training data. They are not official UCP policies or a live institutional service. The separate instructor scenario pack was unavailable during implementation; its actual constraints and change event must be reconciled before final submission.

## 2. Environment analysis

| PEAS element | This scenario |
| --- | --- |
| Performance | Relevant evidence, supported citations, appropriate tool choice, successful context recall, justified replanning and no unconfirmed ticket creation |
| Environment | Local user interface, five knowledge resources, user preference/incident store, simulated service state and ticket database |
| Actuators | Text replies, knowledge searches, authorized memory writes, service queries, ticket drafts and separately confirmed simulated ticket creation |
| Sensors | User messages, session context, stored facts, retrieved passages and actual MCP results |

The environment is partially observable: the agent cannot directly inspect the user's laptop. It is sequential because previous steps and follow-ups affect later advice. It is dynamic because service state can change between requests. It has discrete messages and tool actions. The synthetic service fixture is deterministic, while language-model responses can vary. The process is cooperative with a human user; no competing AI agent is implemented.

## 3. Agent architecture and design pattern

The architecture in `architecture.md` uses a single tool-calling agent with bounded model/tool iterations. LangChain `create_agent` supplies the model/tool execution loop. The Python application manages identities, session messages, persistence, MCP connection lifecycle and confirmation boundaries.

At each turn the application combines the role prompt, current user preferences, previous incident summaries and recent conversation messages. The LLM chooses an available tool based on the request. Tools return observable results to the model, which then responds or selects another tool. This supports a tool-use reasoning/action pattern without requiring disclosure of private chain-of-thought.

The model does not receive a tool that can approve a ticket. It can propose a draft only. A separate user command or button approves that draft, after which a real MCP call creates the saved simulated ticket. The server checks the original user and session. Repeated confirmation returns the same ticket.

## 4. Short-term and long-term memory

Short-term memory is a process-local dictionary keyed by both user and session. It retains recent messages, including tool outputs, for up to ten complete user turns. Starting a new conversation changes the session ID and begins with empty chat history. This lets a follow-up refer to the earlier operating system or already attempted steps.

Long-term memory uses SQLite tables for explicit preferences and incident summaries. Preferences are limited to operating system, response style and device type, with source session and update timestamp. Memory writes require explicit permission in the user turn or the interface control. The application checks that permission outside the model. Credentials must not be saved. A new process retrieves relevant records for the same user without replaying the prior conversation. A different user gets a separate namespace.

The use of one SQLite file for several tables does not merge their purposes: memory records describe users and past incidents; service and ticket records describe simulated operations. Document knowledge is stored separately in Pinecone.

## 5. Retrieval-augmented generation

The five distinct resources are Wi-Fi troubleshooting, VPN troubleshooting, account recovery, printing, and escalation/priority policy. `data/source_manifest.json` records their origin, titles, IDs, versions and synthetic status. Each guide contains several substantive sections.

The ingestion script loads Markdown resources, preserves headings and creates overlapping chunks of up to 220 words with 40-word overlap. The independent `src/embeddings.py` module runs all-MiniLM-L6-v2 locally through ONNX Runtime, mean-pools attention-masked token embeddings and normalizes 384-dimensional vectors. Its tokenizer truncates at 256 tokens; full passage text remains in metadata. Documents and queries use the same model. Pinecone stores vectors, text, provenance, source hashes and citation IDs in a vector-based cosine index.

Retrieval requests up to four passages from Pinecone, accepting cosine scores of at least 0.25. This heuristic needs calibration and is not proof of relevance. The prompt requires evidence supporting the particular claim. Responses cite IDs such as `[WIFI:2]`. The application flags recognized citation IDs not retrieved in this session, but cannot fully prove semantic entailment.

Ingestion uses stable IDs and upserts, so repeating the same corpus does not duplicate IDs. A resource/model fingerprint is appended to the configured namespace. Changed resources use a new namespace without deleting unrelated vectors. Old namespaces are retained until intentionally cleaned up. Pinecone is eventually consistent, so acknowledged upserts may take time to appear in queries. User facts are never ingested as policy documents.

## 6. Functional MCP integration

The official MCP Python SDK's pinned 1.x maintenance line provides the stdio client and FastMCP server. The client launches the server with the same project interpreter as a child process, initializes the protocol, discovers the tool list and invokes tools using `call_tool`. The model sees wrappers bound to the current user's context, not arbitrary user-ID parameters.

The server exposes `get_service_status`, `create_ticket` and `get_ticket_status`. Service results contain a simulation marker and timestamp. Ticket creation requires an approved user/session draft and is idempotent. This is an actual protocol interaction between processes, not an ordinary HTTP call or a direct function call labeled MCP. Server diagnostics go to stderr so stdout remains the protocol channel.

## 7. Prompt engineering justification

The actual prompt is `src/prompts/system_prompt.txt`.

| Prompt rule | Reason |
| --- | --- |
| Defined role and synthetic scope | Prevents the assistant from presenting fictional guidance as official institutional policy |
| Retrieve before procedural/policy advice | Grounds advice in the provided knowledge resources |
| Use status tools for current observations | Separates static manuals from changing service state |
| Cite actual retrieved IDs; disclose gaps | Makes the evidence inspectable and discourages unsupported claims |
| Distinguish session context from persistent facts | Prevents false claims of remembering an entire old conversation |
| Save only authorized relevant memory | Makes persistence intentional and user-scoped |
| Prepare drafts, require separate confirmation | Preserves human oversight; application/server enforcement supports the prompt |
| Revise plans when evidence changes | Demonstrates adaptation rather than repeating an obsolete checklist |
| Treat external text as data | Keeps document instructions from overriding the agent's role |
| Report failures honestly | Prevents failed tools or writes from being presented as successful actions |

## 8. Planning and replanning demonstration

Initial evidence: one Windows 11 laptop cannot connect, and the simulated Wi-Fi status is operational. The initial plan checks network visibility, Wi-Fi/airplane settings, the precise symptom and appropriate device-specific recovery. The agent should ask for missing details and cite relevant guide sections.

Change event: the fixture changes Wi-Fi status to outage and the user reports several affected laptops. The agent requests a fresh observation, retrieves the outage procedure, and revises the plan. It stops repeated local resets, describes the shared-service evidence, suggests a permitted alternative or waiting for updates, and offers escalation without inventing recovery time.

This event illustrates a provisional scenario constraint. The actual instructor-provided change event takes precedence when available. Logs and transcripts show observable decisions, tool outputs and revised advice; no claim is made that a remote machine was repaired.

## 9. Verification and reproducibility

Run the commands in `README.md`. Automated checks cover new-process persistence, user isolation, confirmation, idempotency, service state, real stdio discovery/ticket round trips and the agent loop with controlled models. Offline RAG checks use actual neural embeddings and a named Pinecone index double to verify adapter contracts. The separate cloud test was explicitly enabled and passed against the configured Pinecone index; it remains opt-in for ordinary test runs.

The live demonstration used Claude Sonnet 4.6 through OpenRouter, Pinecone and the real MCP service. All eleven checks passed: retrieval, model-selected MCP status query, short-term recall, persistent memory write, recall in a new process, outage observation, outage-aware reply, ticket draft, confirmed MCP ticket creation, ticket lookup and missing-evidence disclosure. The full JSON evidence is under `evidence/live_demo/465a8d8c36/`. Its prompts and explicit scripted user confirmation are recorded alongside actual model responses and tool outputs.

Observed results are recorded in `../evidence/verification.md`. The selected provider and model were tested with the configured credentials. Recheck the live connections before assessment if keys, model access or the cloud index change.

## 10. Limitations and future work

The local user selector is not authentication. Knowledge and services are synthetic, not live university data. The current loader supports the included Markdown resources rather than arbitrary file formats. Retrieval uses a small corpus and heuristic distance threshold, without a separate reranker or entailment checker. Long conversations are truncated rather than summarized. API-backed chat depends on the configured model's tool support and availability. A local ONNX model must be downloaded once. Citation-ID validation cannot establish that every answer is semantically correct.

Useful extensions are authorized institutional resources, authenticated identities, a tested retrieval evaluation set, configurable retention/deletion, deeper failure/recovery checks and adaptation to the instructor's scenario pack. These are future work rather than implemented claims.

## References

- Assignment 2 supplied PDF, pages 1-4.
- [LangChain agents](https://docs.langchain.com/oss/python/langchain/agents).
- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling).
- [MCP Python SDK v1 documentation](https://py.sdk.modelcontextprotocol.io/v1/).
- [Pinecone vector operations](https://sdk.pinecone.io/python/how-to/vectors/upsert-and-query.html).
- [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility).

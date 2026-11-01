# Reproducible marking demonstration

Use the project interpreter. Configure both a tool-calling model and Pinecone in `.env`, then run ingestion. Until details are supplied, only local preparation and offline checks are verified. Read `README.md` for commands. Use synthetic data only.

1. **Architecture and prompt:** show `docs/architecture.md` and `src/prompts/system_prompt.txt`. Explain the single primary agent and separate memory/knowledge roles.
2. **RAG and tool selection:** ask “My Windows 11 laptop cannot connect to Campus-Lab Wi-Fi. Check current Wi-Fi status and consult the guide before suggesting steps.” Expand Sources and actions. Point out the actual source IDs and simulated MCP result. Responses depend on the real configured model.
3. **Short-term memory:** ask “Which operating system did I mention?” Then say “I already checked airplane mode; what next?” Verify that the assistant uses the current history and retrieved guidance.
4. **Long-term memory:** say “Remember my operating system is Windows 11 and I prefer numbered steps.” Inspect Saved preferences. Stop and restart the application, then use the same demo user with a new session. Ask for the saved preferences. No old transcript is injected. `scripts/run_demo.py` additionally performs recall in a separate Python process.
5. **Five-resource proof:** show the Knowledge library tab, source manifest and `evidence/ingestion.json`. Explain word chunks, local embeddings, Pinecone persistence and citations. Show automated retrieval checks for each resource.
6. **Change event:** run `scripts/set_service.py wifi outage`. Ask “Several laptops now fail. Check Wi-Fi again and revise your earlier plan.” Verify the new outage observation, retrieved outage guidance and revised advice. Do not claim the actual instructor event was supplied.
7. **Human oversight and MCP write:** ask for a simulated Wi-Fi ticket. Show the draft before confirmation. Click Confirm and create ticket or enter the exact `/confirm D-id`. Show the returned HD ticket ID and retrieve its status. Repeating confirmation must return the same ID.
8. **Missing evidence:** ask for the exact official UCP exam rescheduling policy. The assistant should disclose that its synthetic helpdesk documents do not establish this policy.
9. **Errors and tests:** show `evidence/test_results.txt`, real MCP logs and recorded verification limitations. Do not expose `.env` or secrets. Restore Wi-Fi to operational with the fixture script when finished.

The automatic live demo writes an isolated run folder under `evidence/live_demo/`. Its outputs are actual observations, not a guaranteed answer script. Review `checks` and the full transcripts before claiming the demonstration passed.

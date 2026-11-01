import asyncio
import json
import uuid
from src.config import Settings, ROOT
import streamlit as st
from src.agent import HelpdeskAgent

st.set_page_config(page_title="Campus Helpdesk", page_icon="💬", layout="wide")
st.markdown("""<style>
.stApp { background: #f5f7fb; }
[data-testid="stSidebar"] { background: #10263b; }
[data-testid="stSidebar"] * { color: #e5eef6; }
[data-testid="stSidebar"] input { color: #10263b; }
[data-testid="stSidebar"] button p { color: #10263b; }
h1,h2,h3 { color: #10263b; }
[data-testid="stChatMessage"] { background: white; border: 1px solid #e0e8ef; border-radius: 12px; }
.eyebrow { color: #087e8b; font-size: 12px; font-weight: 700; letter-spacing: 2px; }
.hero { padding: 10px 0 20px; }
</style>""", unsafe_allow_html=True)

if "runtime" not in st.session_state:
    st.session_state.runtime = HelpdeskAgent(Settings())
    st.session_state.session_id = uuid.uuid4().hex[:12]
    st.session_state.chat = []
    st.session_state.active_user = "student"
agent = st.session_state.runtime
knowledge_status = agent.knowledge.status()

with st.sidebar:
    st.markdown("### CAMPUS / HELPDESK")
    st.caption("Assignment 2 · Scenario 23")
    user = st.text_input("Demo user", value="student", max_chars=50).strip() or "student"
    if user != st.session_state.active_user:
        st.session_state.active_user = user
        st.session_state.session_id = uuid.uuid4().hex[:12]
        st.session_state.chat = []
    if st.button("＋ New conversation", use_container_width=True):
        st.session_state.session_id = uuid.uuid4().hex[:12]
        st.session_state.chat = []
        st.rerun()
    st.caption(f'Session: {st.session_state.session_id}')
    st.divider()
    st.markdown("**Saved preferences**")
    facts = agent.store.facts(user)
    if facts:
        for key, value in facts.items():
            st.write(f'{key.replace("_", " ").title()}: {value}')
    else:
        st.caption('Say “Remember that I use Windows 11” to save a preference.')
    allow_memory = st.checkbox("Allow saving relevant memory this turn", value=False)
    st.divider()
    st.caption("All campus policies, services and tickets here are simulated. Do not enter passwords or private data.")

st.markdown('<div class="hero"><div class="eyebrow">YOUR CAMPUS SUPPORT DESK</div>'
            '<h1>Let’s work through it.</h1><p>Clear next steps, backed by the helpdesk guides.</p></div>',
            unsafe_allow_html=True)
chat_tab, knowledge_tab, about_tab = st.tabs(["Conversation", "Knowledge library", "Project overview"])


def show_result(result):
    st.markdown(result["answer"])
    if not result["success"]:
        st.caption("This turn could not be fully verified. Review the message and evidence.")
    if result.get("sources") or result.get("events"):
        with st.expander("Sources and actions"):
            for source in result.get("sources", []):
                st.markdown(f'**[{source["citation"]}] {source["title"]}** · {source["heading"]}')
                st.caption("Synthetic training resource")
                st.write(source["text"])
            if result.get("events"):
                st.json(result["events"], expanded=False)


with chat_tab:
    if not agent.settings.model or not agent.settings.api_key and agent.settings.provider == "openai_compatible":
        st.info("Configure LLM_MODEL, LLM_BASE_URL and LLM_API_KEY in .env, then restart the app to enable chat.")
    if knowledge_status["state"] != "connected":
        st.info(knowledge_status["message"] + " The local guides remain available in the Knowledge library.")
    elif not knowledge_status["indexed_chunks"]:
        st.warning("Upload the knowledge documents to Pinecone before asking procedural questions.")
    if not st.session_state.chat:
        st.markdown("Try: **My Windows 11 laptop cannot connect to campus Wi-Fi.**")
        st.caption("You can also ask about VPN, printing, account access or a simulated support ticket.")
    for entry in st.session_state.chat:
        with st.chat_message(entry["role"]):
            if entry["role"] == "user":
                st.write(entry["text"])
            else:
                show_result(entry["result"])
    for draft in agent.store.pending(user, st.session_state.session_id):
        with st.container(border=True):
            st.markdown(f'**Review ticket draft · {draft["id"]}**')
            st.write(draft["summary"])
            st.caption(f'Category: {draft["category"]} · Creates a simulated ticket only')
            if st.button("Confirm and create ticket", key=draft["id"]):
                with st.spinner("Creating the confirmed ticket…"):
                    result = asyncio.run(agent.confirm_ticket(draft["id"], user, st.session_state.session_id))
                st.session_state.chat.append({"role": "assistant", "result": result})
                st.rerun()
    text = st.chat_input("Describe the issue or ask a follow-up…", max_chars=8000)
    if text:
        st.session_state.chat.append({"role": "user", "text": text})
        with st.spinner("Checking the available evidence…"):
            result = asyncio.run(agent.run(text, user, st.session_state.session_id, allow_memory=allow_memory))
        st.session_state.chat.append({"role": "assistant", "result": result})
        st.rerun()

with knowledge_tab:
    manifest = json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8"))
    left, right = st.columns(2)
    left.metric("Knowledge resources", len(manifest))
    right.metric("Pinecone passages", knowledge_status["indexed_chunks"] if knowledge_status["indexed_chunks"] is not None else "Pending")
    st.caption(f'{len(agent.knowledge.records)} passages prepared locally. Remote ingestion is verified only after Pinecone is connected.')
    st.caption("These resources are fictional teaching materials, separate from saved user preferences.")
    for item in manifest:
        with st.expander(f'{item["id"]} · {item["title"]}'):
            st.caption(f'Version {item["version"]} · {item["origin"]}')
            st.markdown((ROOT / item["path"]).read_text(encoding="utf-8"))

with about_tab:
    st.markdown("### One agent, connected evidence")
    st.write("The assistant combines a configured LLM with session history, persistent preferences, document retrieval and a local MCP tool service.")
    st.image((ROOT / "docs/architecture.svg").read_text(encoding="utf-8"),
             caption="Scenario 23 architecture · one primary agent")
    st.markdown("**Suggested demo:** ask for help → ask a follow-up → save a preference → start a new conversation → check service status → introduce an outage using the scenario script → request and confirm a ticket.")
    st.caption("The local user selector demonstrates memory isolation; it is not production authentication.")
    st.write("Report and architecture: docs/report.md and docs/architecture.md")

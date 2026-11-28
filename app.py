"""
Streamlit chat UI for the Cloud Operations AI Agent.

Run:  streamlit run app.py
(The mock API must be running: uvicorn mock_api.main:app --reload)
"""
import json

import httpx
import streamlit as st

from agent.agent import Agent
from agent.context import ConversationContext
from agent.errors import AgentError
from agent.llm_client import SYSTEM_PROMPT, MODEL
from agent.tools import BASE_URL

st.set_page_config(page_title="Cloud Ops AI Agent", page_icon="☁️")


@st.cache_resource
def get_agent():
    return Agent()


def load_trace(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def api_is_up() -> bool:
    try:
        return httpx.get(f"{BASE_URL}/projects", timeout=2.0).status_code == 200
    except httpx.HTTPError:
        return False


def render_trace(trace):
    """Show tool calls and token usage for one agent run."""
    if not trace:
        return
    tool_steps = [s for s in trace["steps"] if s["type"] == "tool_call"]
    errors = [s for s in trace["steps"] if s["type"] == "error"]
    usage = trace.get("token_usage", {})
    label = (
        f"Details · {len(tool_steps)} tool call(s) · "
        f"{usage.get('total_tokens', 0)} tokens · {trace['total_duration_ms']} ms"
    )
    with st.expander(label):
        for step in tool_steps:
            st.markdown(f"**{step['tool']}** `{json.dumps(step['input'])}`")
            st.code(step["output"], language="json")
        for err in errors:
            st.error(f"[{err['source']}] {err['message']}")
        st.caption(
            f"Run ID: {trace['run_id']} · prompt {usage.get('prompt_tokens', 0)} / "
            f"completion {usage.get('completion_tokens', 0)} tokens"
        )


# ---------- setup ----------
try:
    agent = get_agent()
except ValueError as e:
    st.error(f"Configuration error: {e}")
    st.stop()

if "context" not in st.session_state:
    st.session_state.context = ConversationContext(SYSTEM_PROMPT)
    st.session_state.chat = []   # [{role, content, trace}] — display history only

# ---------- sidebar ----------
with st.sidebar:
    st.header("☁️ Cloud Ops Agent")
    st.caption(f"Model: `{MODEL}`")
    if api_is_up():
        st.success(f"Cloud API online ({BASE_URL})")
    else:
        st.error(f"Cloud API unreachable at {BASE_URL}.\n\nRun `uvicorn mock_api.main:app --reload`")

    if st.button("New conversation", use_container_width=True):
        st.session_state.context.reset()
        st.session_state.chat = []
        st.rerun()

    st.subheader("Try asking")
    examples = [
        "List all projects",
        "Find all stopped VMs inactive for more than 7 days",
        "Which VMs have high CPU usage?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex
            st.rerun()

# ---------- chat ----------
st.title("Cloud Operations AI Agent")

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        render_trace(msg.get("trace"))

prompt = st.chat_input("Ask about your cloud infrastructure...")
prompt = prompt or st.session_state.pop("pending", None)

if prompt:
    st.session_state.chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer, trace_path = agent.run(prompt, st.session_state.context)
                trace = load_trace(trace_path)
                st.markdown(answer)
            except AgentError as e:
                answer = f"⚠️ {e}"
                trace = load_trace(e.trace_path)
                st.error(str(e))
        render_trace(trace)

    st.session_state.chat.append({"role": "assistant", "content": answer, "trace": trace})

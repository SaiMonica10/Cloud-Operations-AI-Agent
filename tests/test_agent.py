"""
Full agent loop with a scripted fake LLM and the in-process mock API.
Checks answers, tool chaining, context across turns, error handling and traces.
"""
import json
from types import SimpleNamespace as NS

import openai
import pytest
from fastapi.testclient import TestClient

import agent.agent as agent_module
import agent.llm_client as llm_module
from agent.agent import Agent
from agent.context import ConversationContext
from agent.errors import AgentError, APIUnavailableError, LLMError
from agent.llm_client import SYSTEM_PROMPT, LLMClient
from mock_api.main import app
from tests.conftest import FakeLLM, FlakyClient, llm_answer, llm_tools, make_dispatcher, tool_call


@pytest.fixture
def make_agent(monkeypatch, tmp_path):
    """Build an Agent wired to a FakeLLM. Traces are written to a temp dir, not logs/."""
    monkeypatch.chdir(tmp_path)

    def factory(script, http_client_factory=lambda: TestClient(app)):
        monkeypatch.setattr(agent_module, "ToolDispatcher", lambda: make_dispatcher(http_client_factory()))
        agent = Agent()
        agent.llm = FakeLLM(script)
        return agent

    return factory


def load_trace(path):
    with open(path) as f:
        return json.load(f)


def steps_of(trace, step_type):
    return [s for s in trace["steps"] if s["type"] == step_type]


# ---------- the three demo scenarios ----------

def test_scenario1_multistep_inactive_vm_query(make_agent):
    stopped = ["vm-002", "vm-003", "vm-005", "vm-006", "vm-009", "vm-010"]
    agent = make_agent([
        llm_tools(tool_call("c0", "list_vms", '{"status": "stopped"}')),
        llm_tools(*[tool_call(f"c{i}", "get_vm_activity", json.dumps({"vm_id": v})) for i, v in enumerate(stopped, 1)]),
        llm_answer("vm-002, vm-005, vm-006, vm-010"),
    ])

    answer, trace_path = agent.run("Find stopped VMs inactive for more than 7 days")

    assert answer == "vm-002, vm-005, vm-006, vm-010"
    trace = load_trace(trace_path)
    assert trace["success"] is True
    assert [s["tool"] for s in steps_of(trace, "tool_call")] == ["list_vms"] + ["get_vm_activity"] * 6

    # The LLM really received the activity data it needed to filter
    tool_results = [json.loads(m["content"]) for m in agent.llm.received[-1] if m["role"] == "tool"]
    inactive = {r["vm_id"] for r in tool_results if isinstance(r, dict) and r["days_inactive"] > 7}
    assert inactive == {"vm-002", "vm-005", "vm-006", "vm-010"}


def test_scenario2_followup_uses_session_context(make_agent):
    agent = make_agent([
        llm_tools(tool_call("c1", "list_vms", '{"project_id": "project-alpha"}')),
        llm_answer("Project Alpha: vm-001 running, vm-002 and vm-003 stopped"),
        llm_answer("vm-002 and vm-003 are stopped"),   # follow-up answered from history
    ])
    context = ConversationContext(SYSTEM_PROMPT)

    agent.run("Give me a summary of VMs in Project Alpha", context)
    _, trace_path = agent.run("Which of those are stopped?", context)

    # Turn 2's prompt contained turn 1's question and tool results...
    contents = [m.get("content") or "" for m in agent.llm.received[-1]]
    assert "Give me a summary of VMs in Project Alpha" in contents
    assert any("vm-003" in c for c in contents if c.startswith("["))
    # ...so no tools were needed
    assert steps_of(load_trace(trace_path), "tool_call") == []


def test_scenario3_api_failure_mid_execution(make_agent):
    agent = make_agent(
        [
            llm_tools(tool_call("c1", "list_vms", '{"status": "stopped"}')),
            llm_tools(tool_call("c2", "get_vm_activity", '{"vm_id": "vm-002"}')),
        ],
        http_client_factory=lambda: FlakyClient(ok_calls=1),   # list_vms works, then the API dies
    )
    context = ConversationContext(SYSTEM_PROMPT)
    history_before = len(context.messages)

    with pytest.raises(APIUnavailableError) as exc:
        agent.run("Find stopped VMs inactive for more than 7 days", context)

    assert "couldn't reach the cloud API" in str(exc.value)
    assert load_trace(exc.value.trace_path)["success"] is False
    assert len(context.messages) == history_before   # failed turn rolled back


# ---------- agent loop ----------

def test_llm_recovers_from_bad_tool_argument(make_agent):
    agent = make_agent([
        llm_tools(tool_call("c1", "get_vm_activity", "{}")),                   # missing vm_id
        llm_tools(tool_call("c2", "get_vm_activity", '{"vm_id": "vm-002"}')),  # LLM corrects itself
        llm_answer("vm-002 has been inactive for 15 days"),
    ])

    answer, trace_path = agent.run("How long has vm-002 been inactive?")

    assert "15 days" in answer
    trace = load_trace(trace_path)
    assert trace["success"] is True
    assert steps_of(trace, "error")[0]["source"] == "tool:get_vm_activity"


def test_max_iterations_stops_the_loop(make_agent, monkeypatch):
    monkeypatch.setattr(agent_module, "MAX_ITERATIONS", 2)
    agent = make_agent([llm_tools(tool_call(f"c{i}", "list_projects", "")) for i in range(2)])

    with pytest.raises(AgentError, match="within 2 steps") as exc:
        agent.run("loop forever")

    assert load_trace(exc.value.trace_path)["success"] is False


def test_token_usage_is_recorded_in_trace(make_agent):
    usages = [
        {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
        {"prompt_tokens": 200, "completion_tokens": 20, "total_tokens": 220},
    ]

    class MeteredFakeLLM(FakeLLM):
        def call(self, messages, tools):
            self.last_usage = usages[len(self.received)]
            return super().call(messages, tools)

    agent = make_agent([])
    agent.llm = MeteredFakeLLM([
        llm_tools(tool_call("c1", "list_projects", "")),
        llm_answer("3 projects"),
    ])

    _, trace_path = agent.run("How many projects?")

    assert load_trace(trace_path)["token_usage"] == {"prompt_tokens": 300, "completion_tokens": 30, "total_tokens": 330}


# ---------- LLM client ----------

def test_llm_retries_with_backoff_then_gives_up(monkeypatch):
    waits = []
    monkeypatch.setattr(llm_module.time, "sleep", waits.append)   # record waits instead of sleeping
    client = LLMClient()

    def always_down(**_):
        raise openai.APIConnectionError(request=None)

    monkeypatch.setattr(client._client.chat.completions, "create", always_down)

    with pytest.raises(LLMError, match="unavailable after 3 attempts"):
        client.call([], [])
    assert waits == [5, 10]   # exponential backoff between the 3 attempts


def test_empty_llm_response_is_rejected():
    with pytest.raises(LLMError, match="no choices"):
        LLMClient._extract_message(NS(choices=[]))

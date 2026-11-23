"""
Full agent loop with a scripted fake LLM and the in-process mock API.
Checks answers, tool chaining, context across turns, error handling and traces.
"""
import json
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

import agent.agent as agent_module
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


# ---------- success ----------

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
    tools_used = [s["tool"] for s in steps_of(trace, "tool_call")]
    assert tools_used == ["list_vms"] + ["get_vm_activity"] * 6

    # The LLM really received the activity data it needed to filter
    last_prompt = agent.llm.received[-1]
    tool_results = {json.loads(m["content"])["vm_id"]: json.loads(m["content"])
                    for m in last_prompt if m["role"] == "tool" and m["content"].startswith("{")}
    inactive = {vm for vm, r in tool_results.items() if r["days_inactive"] > 7}
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

    # Turn 2's prompt contained turn 1's question and tool results
    turn2_prompt = agent.llm.received[-1]
    contents = [m.get("content") or "" for m in turn2_prompt]
    assert "Give me a summary of VMs in Project Alpha" in contents
    assert any("vm-003" in c for c in contents if c.startswith("["))
    # ...so no tools were needed
    assert steps_of(load_trace(trace_path), "tool_call") == []


# ---------- failures ----------

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
    trace = load_trace(exc.value.trace_path)
    assert trace["success"] is False
    assert steps_of(trace, "error")[-1]["source"] == "APIUnavailableError"
    assert len(context.messages) == history_before   # failed turn rolled back


def test_max_iterations_raises_agent_error(make_agent, monkeypatch):
    monkeypatch.setattr(agent_module, "MAX_ITERATIONS", 2)
    agent = make_agent([llm_tools(tool_call(f"c{i}", "list_projects", "")) for i in range(2)])

    with pytest.raises(AgentError, match="within 2 steps") as exc:
        agent.run("loop forever")

    trace = load_trace(exc.value.trace_path)
    assert trace["success"] is False
    assert steps_of(trace, "error")[-1]["source"] == "AgentError"


def test_invalid_tool_argument_handled_without_crash(make_agent):
    agent = make_agent([
        llm_tools(tool_call("c1", "get_vm_activity", "{}")),              # missing vm_id
        llm_tools(tool_call("c2", "get_vm_activity", '{"vm_id": "vm-002"}')),  # LLM corrects itself
        llm_answer("vm-002 has been inactive for 15 days"),
    ])

    answer, trace_path = agent.run("How long has vm-002 been inactive?")

    assert "15 days" in answer
    trace = load_trace(trace_path)
    assert trace["success"] is True   # recovered
    errors = steps_of(trace, "error")
    assert errors[0]["source"] == "tool:get_vm_activity"
    assert "Missing required argument 'vm_id'" in errors[0]["message"]


def test_unknown_vm_reported_to_llm(make_agent):
    agent = make_agent([
        llm_tools(tool_call("c1", "get_vm_metrics", '{"vm_id": "vm-999"}')),
        llm_answer("vm-999 does not exist"),
    ])

    _, trace_path = agent.run("CPU for vm-999?")

    tool_msg = [m for m in agent.llm.received[-1] if m["role"] == "tool"][0]
    assert "Not found" in tool_msg["content"]
    assert steps_of(load_trace(trace_path), "error")[0]["source"] == "tool:get_vm_metrics"


def test_llm_failure_becomes_friendly_error(make_agent):
    agent = make_agent([LLMError("The language model returned no choices.")])

    with pytest.raises(LLMError) as exc:
        agent.run("anything")

    assert load_trace(exc.value.trace_path)["success"] is False


def test_unexpected_exception_wrapped_as_agent_error(make_agent):
    agent = make_agent([RuntimeError("boom")])

    with pytest.raises(AgentError, match="Something went wrong inside the agent") as exc:
        agent.run("anything")

    assert steps_of(load_trace(exc.value.trace_path), "error")[-1]["source"] == "unexpected"


# ---------- LLM response validation ----------

@pytest.mark.parametrize(
    "response, expected",
    [
        (NS(choices=[]), "no choices"),
        (NS(choices=None, error={"code": 502}), "returned an error"),
        (NS(choices=[NS(message=None)]), "empty message"),
        (NS(choices=[NS(message=llm_answer("   "))]), "empty answer"),
    ],
)
def test_llm_unexpected_response_raises_llm_error(response, expected):
    with pytest.raises(LLMError, match=expected):
        LLMClient._extract_message(response)

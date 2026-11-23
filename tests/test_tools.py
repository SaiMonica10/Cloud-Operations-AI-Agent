"""ToolDispatcher: tool calls → mock API, and every way a tool call can go wrong."""
import json

import pytest

from agent.errors import APIUnavailableError
from tests.conftest import FlakyClient, make_dispatcher


def test_list_vms_no_filters(dispatcher):
    result, error = dispatcher.execute("list_vms", "{}")
    assert error is None
    assert len(json.loads(result)) == 10


def test_list_vms_status_stopped(dispatcher):
    result, error = dispatcher.execute("list_vms", json.dumps({"status": "stopped"}))
    assert error is None
    vms = json.loads(result)
    assert len(vms) == 6
    assert all(v["status"] == "stopped" for v in vms)


def test_get_vm_activity_valid_id(dispatcher):
    result, error = dispatcher.execute("get_vm_activity", '{"vm_id": "vm-010"}')
    assert error is None
    body = json.loads(result)
    assert set(body) >= {"vm_id", "name", "status", "last_active", "days_inactive"}
    assert body["days_inactive"] == 30


def test_get_vm_activity_invalid_id_returns_error(dispatcher):
    result, error = dispatcher.execute("get_vm_activity", '{"vm_id": "vm-999"}')
    assert error == "Not found: VM 'vm-999' not found"
    assert json.loads(result) == {"error": error}   # the LLM sees the same message


def test_get_vm_metrics_valid_id(dispatcher):
    result, error = dispatcher.execute("get_vm_metrics", '{"vm_id": "vm-001"}')
    assert error is None
    body = json.loads(result)
    assert body["cpu_usage_percent"] == 45.2
    assert body["memory_gb"] == 8


def test_list_projects_accepts_empty_arguments(dispatcher):
    """Some models send "" for tools with no parameters."""
    result, error = dispatcher.execute("list_projects", "")
    assert error is None
    assert len(json.loads(result)) == 3


@pytest.mark.parametrize(
    "tool, arguments, expected",
    [
        ("get_vm_activity", "{}", "Missing required argument 'vm_id'"),
        ("list_vms", "not json", "Invalid call to 'list_vms'"),
        ("list_vms", "[1, 2]", "arguments must be a JSON object"),
        ("delete_everything", "{}", "unknown tool 'delete_everything'"),
    ],
)
def test_malformed_calls_return_error_instead_of_crashing(dispatcher, tool, arguments, expected):
    result, error = dispatcher.execute(tool, arguments)
    assert expected in error
    assert "error" in json.loads(result)


def test_api_down_raises_api_unavailable():
    d = make_dispatcher(FlakyClient(ok_calls=0))
    with pytest.raises(APIUnavailableError, match="couldn't reach the cloud API"):
        d.execute("list_vms", "{}")
    d.close()

"""ToolDispatcher: turns the LLM's tool calls into API requests, and handles what can go wrong."""
import json

import pytest

from agent.errors import APIUnavailableError
from tests.conftest import FlakyClient, make_dispatcher


def test_unknown_vm_returns_error_to_llm(dispatcher):
    result, error = dispatcher.execute("get_vm_activity", '{"vm_id": "vm-999"}')
    assert error == "Not found: VM 'vm-999' not found"
    assert json.loads(result) == {"error": error}   # the LLM sees the same message


def test_missing_argument_returns_error_to_llm(dispatcher):
    result, error = dispatcher.execute("get_vm_activity", "{}")
    assert "Missing required argument 'vm_id'" in error
    assert "error" in json.loads(result)


def test_vm_id_injection_is_blocked():
    """vm_id comes from the LLM; a path like '../projects' must never reach the API."""
    d = make_dispatcher(FlakyClient(ok_calls=0))   # any HTTP request would raise
    result, error = d.execute("get_vm_metrics", '{"vm_id": "../projects"}')
    assert "vm_id must be a plain identifier" in error
    d.close()


def test_api_down_raises_api_unavailable():
    d = make_dispatcher(FlakyClient(ok_calls=0))
    with pytest.raises(APIUnavailableError, match="couldn't reach the cloud API"):
        d.execute("list_vms", "{}")
    d.close()

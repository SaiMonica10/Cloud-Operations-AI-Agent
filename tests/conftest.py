"""
Shared test setup.

- Sets fake OpenRouter config BEFORE any agent module is imported (llm_client checks
  OPENROUTER_MODEL at import time). Tests never call the real LLM.
- Runs the mock API in-process with FastAPI's TestClient — no uvicorn server needed.
"""
import os

os.environ["OPENROUTER_MODEL"] = "test/model"
os.environ["OPENROUTER_API_KEY"] = "test-key"

from types import SimpleNamespace as NS

import httpx
import pytest
from fastapi.testclient import TestClient

from mock_api.main import app
from agent.tools import ToolDispatcher


# ---------- mock API ----------

@pytest.fixture
def api_client():
    with TestClient(app) as client:
        yield client


def make_dispatcher(http_client) -> ToolDispatcher:
    """A ToolDispatcher whose HTTP calls go to the given client instead of localhost:8000."""
    d = ToolDispatcher()
    d._client.close()
    d._client = http_client
    return d


@pytest.fixture
def dispatcher():
    d = make_dispatcher(TestClient(app))
    yield d
    d.close()


class FlakyClient:
    """Serves the first `ok_calls` requests from the mock API, then behaves as if it went down."""

    def __init__(self, ok_calls: int):
        self._real = TestClient(app)
        self._left = ok_calls

    def get(self, *args, **kwargs):
        if self._left == 0:
            raise httpx.ConnectError("Connection refused")
        self._left -= 1
        return self._real.get(*args, **kwargs)

    def close(self):
        self._real.close()


# ---------- fake LLM ----------

def tool_call(call_id: str, name: str, arguments: str):
    return NS(id=call_id, function=NS(name=name, arguments=arguments))


def llm_tools(*calls):
    """An assistant message that asks for tool calls."""
    return NS(content=None, tool_calls=list(calls))


def llm_answer(text: str):
    """An assistant message with a final answer."""
    return NS(content=text, tool_calls=None)


class FakeLLM:
    """Replays a scripted list of assistant messages (or exceptions) and records what it was sent."""

    def __init__(self, script):
        self.script = list(script)
        self.received = []   # snapshot of the messages list for every call
        self.last_usage = None   # same attribute the real LLMClient exposes

    def call(self, messages, tools):
        self.received.append(list(messages))
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

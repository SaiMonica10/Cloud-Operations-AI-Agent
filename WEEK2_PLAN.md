# Week 2 Plan — Cloud Operations AI Agent

**Assignment deadline:** ~2026-11-25
**Focus:** Improve the existing implementation — no new frameworks or features.

---

## Day 1 — Multi-step Orchestration

**Goal:** Force the agent to call multiple APIs and combine results before answering.

**Problem with current design:**
`list_vms` already returns `last_active`, `cpu_usage`, and `memory_gb` in a single response. The agent can answer most questions in one tool call, which does not demonstrate real multi-step reasoning.

**Changes to make:**

- Strip `last_active` out of the `/vms` response — activity data must come from `/vms/{id}/activity`
- Strip `cpu_usage` and `memory_gb` out of the `/vms` response — metrics must come from `/metrics/{id}`
- Update `mock_api/data/synthetic.py` and all three routers to reflect the split
- Update tool descriptions in `agent/tools.py` so the LLM understands which tool provides what

**Result:**
Answering "find inactive VMs in Project Alpha" now genuinely requires:
`list_projects` → `list_vms(project_id=...)` → `get_vm_activity` for each VM → filter and answer.

---

## Day 2 — Context Management (Multi-turn Conversations)

**Goal:** Support follow-up questions within a single session.

**Problem with current design:**
`ConversationContext` is created fresh inside `run_query()` on every call. Each question starts with a blank slate — there is no memory of what was asked or answered before.

**Changes to make:**

- Move `ConversationContext` creation out of `run_query()` so it lives at the session level
- Add a `context` parameter to `run_query()` so an existing context can be passed in
- Update the interactive loop in `main.py` to create one context at session start and thread it through every query
- Keep single-shot mode (non-interactive) working by creating a fresh context when none is provided

**Result:**
A user can ask "Find stopped VMs inactive for 7+ days" and then follow up with "Which of those belong to Project Alpha?" and the agent will answer correctly using the prior result.

---

## Day 3 — Error Handling and Reliability

**Goal:** Handle every failure mode gracefully and capture failures in execution traces.

**Failure cases to cover:**

| Failure | Where it happens | Expected behavior |
|---|---|---|
| VM ID does not exist | `get_vm_activity`, `get_vm_metrics` | API returns 404 → agent logs error, tells user the VM was not found |
| Mock API is down | Any tool call | `httpx.ConnectError` → agent logs error, returns friendly message |
| LLM returns unexpected response | `llm_client.py` | No `choices`, empty content, or missing fields → catch and raise `AgentError` |
| Max iterations reached | `agent.py` loop | Raise `AgentError` with iteration count, log as failure in trace |
| Malformed tool arguments | `tools.py` dispatcher | Missing required param → catch `KeyError`/`ValueError`, return error JSON to LLM |

**For each case:**
- Catch the specific exception
- Add a `{"type": "error", "message": "...", "timestamp": "..."}` step to the tracer
- Return a user-readable message instead of a stack trace

---

## Day 4 — Automated Testing

**Goal:** Cover successful execution, failures, and edge cases with pytest.

**Test files to create:**

**`tests/test_mock_api.py`** — test FastAPI endpoints directly
- `GET /vms` returns all 10 VMs
- `GET /vms?status=stopped` returns only stopped VMs
- `GET /vms?project_id=project-alpha` returns only Project Alpha VMs
- `GET /vms/{id}/activity` returns correct data for a valid VM
- `GET /vms/{id}/activity` returns 404 for an invalid VM ID
- `GET /metrics/{id}` returns correct data for a valid VM
- `GET /projects` returns all 3 projects

**`tests/test_tools.py`** — test the ToolDispatcher
- `list_vms` with no filters returns all VMs
- `list_vms` with `status=stopped` returns filtered list
- `get_vm_activity` with valid ID returns expected fields
- `get_vm_activity` with invalid ID returns an error response
- `get_vm_metrics` with valid ID returns expected fields

**`tests/test_agent.py`** — test the full agent loop (mock LLM responses)
- Scenario 1: multi-step inactive VM query completes successfully
- Scenario 2: follow-up question using session context resolves correctly
- Scenario 3: API failure mid-execution returns graceful error message
- Max iterations exceeded raises `AgentError`
- Invalid tool argument is handled without crashing

**Target:** ~15–20 test cases, all passing with `pytest tests/ -v`.

---

## Day 5 — Demo Preparation and Polish

**Goal:** Three solid, explainable demo scenarios ready for review.

**Scenario 1 — Multi-step query**
> "Find all stopped VMs inactive for more than 7 days."

Expected tool calls: `list_vms(status=stopped)` → `get_vm_activity` for each result → filter by date → answer.
Shows: the agent cannot shortcut with a single API call; it must combine results.

**Scenario 2 — Context / follow-up**
> Turn 1: "Give me a summary of VMs in Project Alpha."
> Turn 2: "Which of those have CPU usage above 50%?"

Expected: Turn 2 uses the VM list from Turn 1 without re-fetching projects.
Shows: session-level context threads correctly across queries.

**Scenario 3 — Failure recovery**
> Simulate the mock API going down mid-execution (stop the server between tool calls).

Expected: agent logs the connection error in the trace, returns a friendly message, does not crash.
Shows: error handling and trace capture working end-to-end.

**Prepare to explain:**
- Why a manual agentic loop instead of a framework like LangChain
- How context is threaded across turns and what happens if the history gets too long
- What the tracer captures and how you would use it to debug a production failure
- What you would change or add with more time

---

## Summary

| Day | Focus | Key deliverable |
|---|---|---|
| 1 | Multi-step orchestration | Reworked API data model, agent must chain 3+ tool calls |
| 2 | Context management | Session-level context, follow-up questions work |
| 3 | Error handling | All failure modes caught, logged in traces |
| 4 | Automated testing | ~15 pytest cases covering success, failure, edge cases |
| 5 | Demo prep | Three rehearsed scenarios, architecture explanation ready |

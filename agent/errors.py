class AgentError(Exception):
    """Ends the current turn. str(e) is shown to the user, so keep it readable."""
    trace_path = None   # set by the agent once the failure trace is saved


class LLMError(AgentError):
    """The LLM call failed or returned something unusable."""


class APIUnavailableError(AgentError):
    """The cloud API can't be reached — the LLM can't fix that, so stop the turn."""

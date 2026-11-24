import os
import time
import openai
from openai import OpenAI
from dotenv import load_dotenv
from agent.errors import LLMError

load_dotenv()

SYSTEM_PROMPT = """You are a Cloud Operations AI Agent. You help users query and analyze cloud infrastructure.

You have tools to query VMs, projects, and metrics. Use them to gather real data before answering.
Never assume or make up infrastructure details — always base answers on tool results.

This is a multi-turn conversation. For follow-up questions ("those", "them", "which of these"),
reuse data already returned by earlier tool calls in this conversation. Only call tools again
for data you do not already have.

When you have everything you need, give a clear and concise final answer."""

MODEL = os.getenv("OPENROUTER_MODEL")
if not MODEL:
    raise ValueError("OPENROUTER_MODEL is not set in .env file ")

MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 15

# Temporary problems worth retrying; anything else fails immediately
RETRYABLE_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,   # also covers APITimeoutError
    openai.InternalServerError,
)


class LLMClient:
    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set in your .env file")

        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            max_retries=0,  # we handle retries ourselves for better logging
        )

    def call(self, messages: list, tools: list):
        """Call the LLM and return the assistant message. Raises LLMError on any failure."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                if response.usage:
                    print(f"[LLM] tokens — prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens}, total: {response.usage.total_tokens}")
                break
            except RETRYABLE_ERRORS as e:
                if attempt == MAX_RETRIES:
                    raise LLMError(
                        f"The language model is unavailable after {MAX_RETRIES} attempts "
                        f"({type(e).__name__}). Please try again in a moment."
                    ) from e
                print(f"[LLM] {type(e).__name__} (attempt {attempt}/{MAX_RETRIES}). Waiting {RETRY_WAIT_SECONDS}s...")
                time.sleep(RETRY_WAIT_SECONDS)
            except openai.NotFoundError as e:
                raise LLMError(
                    f"Model '{MODEL}' not found on OpenRouter. Update OPENROUTER_MODEL in your .env file."
                ) from e
            except openai.AuthenticationError as e:
                raise LLMError("OpenRouter rejected the API key. Check OPENROUTER_API_KEY in your .env file.") from e
            except openai.APIError as e:
                raise LLMError(f"The language model request failed: {e}") from e

        return self._extract_message(response)

    @staticmethod
    def _extract_message(response):
        """Validate the response shape before the agent touches it."""
        # OpenRouter can return HTTP 200 with an error in the body and no choices
        error = getattr(response, "error", None)
        if error:
            raise LLMError(f"The language model returned an error: {error}")
        if not getattr(response, "choices", None):
            raise LLMError("The language model returned no choices.")
        message = response.choices[0].message
        if message is None:
            raise LLMError("The language model returned an empty message.")
        if not message.tool_calls and not (message.content or "").strip():
            raise LLMError("The language model returned an empty answer.")
        return message

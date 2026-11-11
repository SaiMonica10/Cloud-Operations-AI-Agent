import os
import time
import openai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a Cloud Operations AI Agent. You help users query and analyze cloud infrastructure.

You have tools to query VMs, projects, and metrics. Use them to gather real data before answering.
Never assume or make up infrastructure details — always call a tool to get actual data.

When you have everything you need, give a clear and concise final answer."""

MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 15


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
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
            except openai.RateLimitError as e:
                if attempt == MAX_RETRIES:
                    raise
                print(f"[LLM] Rate limited (attempt {attempt}/{MAX_RETRIES}). Waiting {RETRY_WAIT_SECONDS}s...")
                time.sleep(RETRY_WAIT_SECONDS)
            except openai.NotFoundError:
                raise ValueError(
                    f"Model '{MODEL}' not found on OpenRouter. "
                    "Update OPENROUTER_MODEL in your .env file."
                )

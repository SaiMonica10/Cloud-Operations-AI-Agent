import json
from typing import Optional
from agent.context import ConversationContext
from agent.errors import AgentError
from agent.llm_client import LLMClient, SYSTEM_PROMPT, MODEL
from agent.tools import TOOLS, ToolDispatcher
from agent.tracer import ExecutionTracer

MAX_ITERATIONS = 20


class Agent:
    def __init__(self):
        self.llm = LLMClient()

    def run(self, user_input: str, context: Optional[ConversationContext] = None) -> tuple:
        """
        Run the agent on a user request.
        Pass an existing context to continue a conversation; omit it for a one-off query.
        Returns (final_answer: str, trace_path: str).
        """
        if context is None:
            context = ConversationContext(SYSTEM_PROMPT)   # single-shot mode still works

        checkpoint = context.checkpoint()
        succeeded = False

        tracer = ExecutionTracer()
        dispatcher = ToolDispatcher()

        context.add_user_message(user_input)
        tracer.set_input(user_input)

        print(f"\n[Agent] Run ID : {tracer.run_id}")
        print(f"[Agent] Input  : {user_input}\n")

        try:
            for iteration in range(1, MAX_ITERATIONS + 1):
                print(f"[Agent] Iteration {iteration} — calling LLM...")
                tracer.log_llm_call(iteration, MODEL)

                message = self.llm.call(context.messages, TOOLS)   # raises LLMError on bad responses
                # this sends full histroy ( system prompt + user question + every earlier tool call and result) + tools menu to LLM
                tracer.log_usage(self.llm.last_usage)
                context.add_assistant_message(message)

                # LLM gave a final text answer — we're done
                if not message.tool_calls:
                    final_answer = message.content
                    trace_path = tracer.save(final_answer, success=True)
                    print(f"[Agent] Finished. Trace: {trace_path}")
                    succeeded = True
                    return final_answer, trace_path

                # LLM wants to call tools — execute each one
                for tool_call in message.tool_calls:
                    name = tool_call.function.name
                    raw_args = tool_call.function.arguments
                    print(f"[Agent]   → {name}({raw_args})")

                    result, error = dispatcher.execute(name, raw_args)   # raises APIUnavailableError if API is down

                    try:
                        args_dict = json.loads(raw_args) if isinstance(raw_args, str) and raw_args else {}
                    except json.JSONDecodeError:
                        args_dict = {"_raw": raw_args}   # keep the bad input visible in the trace

                    tracer.log_tool_call(name, args_dict, result)
                    if error:
                        tracer.log_error(error, source=f"tool:{name}")
                        print(f"[Agent]   ✗ {error}")
                    else:
                        preview = result[:120] + ("..." if len(result) > 120 else "")
                        print(f"[Agent]   ← {preview}")

                    context.add_tool_result(tool_call.id, result)

            raise AgentError(
                f"I couldn't finish this request within {MAX_ITERATIONS} steps. "
                "Try asking a more specific question."
            )

        except AgentError as e:
            tracer.log_error(str(e), source=type(e).__name__)
            e.trace_path = tracer.save(str(e), success=False)
            raise

        except Exception as e:
            # Safety net for bugs we didn't anticipate: save the trace, never show a stack trace
            msg = f"Something went wrong inside the agent ({type(e).__name__}: {e}). Details are in the trace."
            tracer.log_error(msg, source="unexpected")
            err = AgentError(msg)
            err.trace_path = tracer.save(msg, success=False)
            raise err from e

        finally:
            if not succeeded:
                context.rollback(checkpoint)   # failed turn leaves no trace in history
            dispatcher.close()

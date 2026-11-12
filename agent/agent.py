import json
from agent.context import ConversationContext
from agent.llm_client import LLMClient, SYSTEM_PROMPT, MODEL
from agent.tools import TOOLS, ToolDispatcher
from agent.tracer import ExecutionTracer

MAX_ITERATIONS = 10


class AgentError(Exception):
    pass

class Agent:
    def __init__(self):
        self.llm = LLMClient()

    def run(self, user_input: str) -> tuple:
        """
        Run the agent on a user request.
        Returns (final_answer: str, trace_path: str).
        """
        context = ConversationContext(SYSTEM_PROMPT)
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

                response = self.llm.call(context.messages,TOOLS)
                message = response.choices[0].message
                context.add_assistant_message(message)

                # LLM gave a final text answer — we're done
                if not message.tool_calls:
                    final_answer = message.content or ""
                    trace_path = tracer.save(final_answer, success=True)
                    print(f"[Agent] Finished. Trace: {trace_path}")
                    return final_answer, trace_path

                # LLM wants to call tools — execute each one
                for tool_call in message.tool_calls:
                    name = tool_call.function.name
                    raw_args = tool_call.function.arguments
                    print(f"[Agent]   → {name}({raw_args})")

                    result = dispatcher.execute(name, raw_args)

                    try:
                        args_dict = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except json.JSONDecodeError:
                        args_dict = {}

                    tracer.log_tool_call(name, args_dict, result)
                    context.add_tool_result(tool_call.id, result)

                    preview = result[:120] + ("..." if len(result) > 120 else "")
                    print(f"[Agent]   ← {preview}")

            raise AgentError(f"Reached max iterations ({MAX_ITERATIONS}) without a final answer")

        except AgentError as e:
            tracer.log_error(str(e))
            trace_path = tracer.save(str(e), success=False)
            raise

        finally:
            dispatcher.close()

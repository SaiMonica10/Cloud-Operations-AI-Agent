import sys
from agent.agent import Agent
from agent.context import ConversationContext
from agent.errors import AgentError
from agent.llm_client import SYSTEM_PROMPT


def main():
    try:
        agent = Agent()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Single-shot mode: python main.py "your question here"
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        try:
            answer, trace = agent.run(user_input)
            print(f"\nAnswer:\n{answer}")
            print(f"\nTrace saved to: {trace}")
        except AgentError as e:
            print(f"\nAgent error: {e}")
            if e.trace_path:
                print(f"Trace saved to: {e.trace_path}")
        return

    # Interactive mode
    print("=" * 50)
    print("  Cloud Operations AI Agent")
    print("  Type 'reset' to start a new conversation, 'exit' to quit")
    print("=" * 50)

    context = ConversationContext(SYSTEM_PROMPT)   # lives for the whole session

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break
        if user_input.lower() == "reset":
            context.reset()
            print("Conversation cleared.")
            continue

        try:
            answer, trace_path = agent.run(user_input, context)
            print(f"\nAgent: {answer}")
            print(f"\n[Trace saved: {trace_path}]")
        except AgentError as e:
            print(f"\nError: {e}")
            if e.trace_path:
                print(f"[Trace saved: {e.trace_path}]")


if __name__ == "__main__":
    main()

import sys
from agent.agent import Agent, AgentError


def main():
    agent = Agent()

    # Single-shot mode: python main.py "your question here"
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        try:
            answer, trace = agent.run(user_input)
            print(f"\nAnswer:\n{answer}")
            print(f"\nTrace saved to: {trace}")
        except AgentError as e:
            print(f"\nAgent error: {e}")
        return

    # Interactive mode
    print("=" * 50)
    print("  Cloud Operations AI Agent")
    print("  Type 'exit' to quit")
    print("=" * 50)

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

        try:
            answer, trace_path = agent.run(user_input)
            print(f"\nAgent: {answer}")
            print(f"\n[Trace saved: {trace_path}]")
        except AgentError as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()

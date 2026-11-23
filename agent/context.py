class ConversationContext:
    def __init__(self, system_prompt: str):
        self.messages = [{"role": "system", "content": system_prompt}]

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, message):
        # Convert the OpenAI response object into a plain dict for the next API call
        msg = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, content: str):
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })
        
    def checkpoint(self) -> int:
        """Remember where the history is before a turn starts."""
        return len(self.messages)

    def rollback(self, checkpoint: int):
        """Undo everything added since the checkpoint (used when a turn fails)."""
        del self.messages[checkpoint:]

    def reset(self):
        """Clear the conversation but keep the system prompt."""
        del self.messages[1:]


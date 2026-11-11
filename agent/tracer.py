import json
import uuid
import time
import os
from datetime import datetime, timezone


class ExecutionTracer:
    def __init__(self):
        self.run_id = str(uuid.uuid4())[:8]
        self.start_time = time.time()
        self.steps = []
        self.user_input = ""

    def set_input(self, user_input: str):
        self.user_input = user_input

    def log_llm_call(self, iteration: int, model: str):
        self.steps.append({
            "step": len(self.steps) + 1,
            "type": "llm_call",
            "iteration": iteration,
            "model": model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def log_tool_call(self, tool_name: str, tool_input: dict, result: str):
        self.steps.append({
            "step": len(self.steps) + 1,
            "type": "tool_call",
            "tool": tool_name,
            "input": tool_input,
            "output": result[:500] if len(result) > 500 else result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def log_error(self, error: str):
        self.steps.append({
            "step": len(self.steps) + 1,
            "type": "error",
            "message": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def save(self, final_answer: str, success: bool) -> str:
        trace = {
            "run_id": self.run_id,
            "user_input": self.user_input,
            "start_time": datetime.fromtimestamp(self.start_time, timezone.utc).isoformat(),
            "total_duration_ms": round((time.time() - self.start_time) * 1000),
            "steps": self.steps,
            "final_answer": final_answer,
            "success": success,
        }

        os.makedirs("logs/traces", exist_ok=True)
        path = f"logs/traces/{self.run_id}.json"
        with open(path, "w") as f:
            json.dump(trace, f, indent=2)

        return path

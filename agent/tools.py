import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("MOCK_API_BASE_URL", "http://localhost:8000")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_vms",
            "description": "List VMs filtered by status (running/stopped/all) and optionally by project_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["running", "stopped", "all"],
                        "description": "Filter VMs by their status. Default is 'all'.",
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Filter by project ID, e.g. 'project-alpha'.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vm_activity",
            "description": "Get the last activity timestamp and status of a specific VM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vm_id": {"type": "string", "description": "The VM ID, e.g. 'vm-001'."},
                },
                "required": ["vm_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vm_metrics",
            "description": "Get CPU usage and memory for a specific VM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vm_id": {"type": "string", "description": "The VM ID, e.g. 'vm-001'."},
                },
                "required": ["vm_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "List all available cloud projects.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

class ToolDispatcher:
    def __init__(self):
        self._client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    def execute(self, tool_name: str, arguments: str) -> str:
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
        except json.JSONDecodeError:
            return json.dumps({"error": "Could not parse tool arguments as JSON"})

        try:
            if tool_name == "list_vms":
                return self._list_vms(args)
            elif tool_name == "get_vm_activity":
                return self._get_vm_activity(args)
            elif tool_name == "get_vm_metrics":
                return self._get_vm_metrics(args)
            elif tool_name == "list_projects":
                return self._list_projects()
            else:
                return json.dumps({"error": f"Unknown tool: '{tool_name}'"})

        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"API returned {e.response.status_code}: {e.response.text}"})
        except httpx.RequestError as e:
            return json.dumps({"error": f"Could not reach mock API: {str(e)}. Is it running?"})

    def _list_vms(self, args: dict) -> str:
        params = {}
        if "status" in args:
            params["status"] = args["status"]
        if "project_id" in args:
            params["project_id"] = args["project_id"]
        r = self._client.get("/vms", params=params)
        r.raise_for_status()
        return r.text

    def _get_vm_activity(self, args: dict) -> str:
        r = self._client.get(f"/vms/{args['vm_id']}/activity")
        r.raise_for_status()
        return r.text

    def _get_vm_metrics(self, args: dict) -> str:
        r = self._client.get(f"/metrics/{args['vm_id']}")
        r.raise_for_status()
        return r.text

    def _list_projects(self) -> str:
        r = self._client.get("/projects")
        r.raise_for_status()
        return r.text

    def close(self):
        self._client.close()

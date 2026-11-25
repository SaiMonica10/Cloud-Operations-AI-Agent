import json
import os
import re
import httpx
from typing import Optional, Tuple
from dotenv import load_dotenv
from agent.errors import APIUnavailableError

load_dotenv()

BASE_URL = os.getenv("MOCK_API_BASE_URL", "http://localhost:8000")
VM_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_vms",
            "description": (
                "List VM inventory: vm_id, name, project_id, status, region. "
                "Filter by status and/or project_id. "
                "Does NOT include activity or metrics — call get_vm_activity "
                "or get_vm_metrics per VM for those."
            ),
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
                        "description": "Filter by project ID, e.g. 'project-alpha'. Use list_projects to find valid IDs.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vm_activity",
            "description": (
                "Get activity for ONE VM: last_active timestamp and days_inactive. "
                "This is the only source of activity data — call it for each VM "
                "when a question involves inactivity or idle time."
            ),
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
            "description": (
                "Get resource metrics for ONE VM: cpu_usage_percent and memory_gb. "
                "This is the only source of CPU/memory data — call it for each VM "
                "when a question involves usage or utilization."
            ),
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
            "description": "List all cloud projects with their project_id, name, region and owner. Use this to map a project name (e.g. 'Project Alpha') to its project_id.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class ToolDispatcher:
    def __init__(self):
        self._client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    def execute(self, tool_name: str, arguments) -> Tuple[str, Optional[str]]:
        """
        Run a tool. Returns (result_json, error_message).
          - Success:            (api_response, None)
          - Recoverable error:  ('{"error": "..."}', "...")  → the LLM sees it and can react
        Raises APIUnavailableError if the API can't be reached at all.
        """
        try:
            args = self._parse_args(arguments)
            if tool_name == "list_vms":
                return self._list_vms(args), None
            elif tool_name == "get_vm_activity":
                return self._get_vm_activity(args), None
            elif tool_name == "get_vm_metrics":
                return self._get_vm_metrics(args), None
            elif tool_name == "list_projects":
                return self._list_projects(), None
            else:
                raise ValueError(f"unknown tool '{tool_name}'")

        except httpx.HTTPStatusError as e:
            msg = self._describe_http_error(e)
        except httpx.RequestError as e:
            raise APIUnavailableError(
                f"I couldn't reach the cloud API at {BASE_URL} ({type(e).__name__}). "
                "Please check that the mock API is running and try again."
            ) from e
        except KeyError as e:
            msg = f"Missing required argument {e} for tool '{tool_name}'"
        except (ValueError, TypeError) as e:
            msg = f"Invalid call to '{tool_name}': {e}"

        return json.dumps({"error": msg}), msg

    @staticmethod
    def _parse_args(arguments) -> dict:
        if arguments in (None, ""):
            return {}   # some models send "" for tools with no parameters
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
        if not isinstance(args, dict):
            raise ValueError(f"arguments must be a JSON object, got {type(args).__name__}")
        return args

    @staticmethod
    def _describe_http_error(e: httpx.HTTPStatusError) -> str:
        status = e.response.status_code
        try:
            body = e.response.json()
            detail = body.get("detail", body) if isinstance(body, dict) else body
        except ValueError:
            detail = e.response.text
        if status == 404:
            return f"Not found: {detail}"
        return f"API returned {status}: {detail}"

    def _list_vms(self, args: dict) -> str:
        params = {}
        if "status" in args:
            params["status"] = args["status"]
        if "project_id" in args:
            params["project_id"] = args["project_id"]
        r = self._client.get("/vms", params=params)
        r.raise_for_status()
        return r.text

    @staticmethod
    def _vm_id(args: dict) -> str:
        """
        vm_id comes from the LLM and goes into a URL path, so allow only plain identifiers.
        Blocks prompt-injected values like '../projects' from reaching other endpoints.
        """
        vm_id = args["vm_id"]
        if not isinstance(vm_id, str) or not VM_ID_PATTERN.fullmatch(vm_id):
            raise ValueError(f"vm_id must be a plain identifier like 'vm-001', got {vm_id!r}")
        return vm_id

    def _get_vm_activity(self, args: dict) -> str:
        r = self._client.get(f"/vms/{self._vm_id(args)}/activity")
        r.raise_for_status()
        return r.text

    def _get_vm_metrics(self, args: dict) -> str:
        r = self._client.get(f"/metrics/{self._vm_id(args)}")
        r.raise_for_status()
        return r.text

    def _list_projects(self) -> str:
        r = self._client.get("/projects")
        r.raise_for_status()
        return r.text

    def close(self):
        self._client.close()

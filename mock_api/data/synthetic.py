from datetime import datetime, timedelta, timezone


def _ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


PROJECTS = [
    {"project_id": "project-alpha", "name": "Project Alpha", "region": "us-east-1", "owner": "team-backend"},
    {"project_id": "project-beta",  "name": "Project Beta",  "region": "us-west-2", "owner": "team-data"},
    {"project_id": "project-gamma", "name": "Project Gamma", "region": "eu-west-1", "owner": "team-frontend"},
]

# Data is deliberately split across three sources, like a real cloud provider:
#   VMS          → inventory only           (served by GET /vms)
#   VM_ACTIVITY  → last activity timestamps (served by GET /vms/{id}/activity)
#   VM_METRICS   → CPU / memory             (served by GET /metrics/{id})
#
# Designed to support all 3 demo scenarios:
# Scenario 1: stopped VMs inactive >7 days → vm-002, vm-005, vm-006, vm-010
# Scenario 2: project-alpha summary → 1 running, 2 stopped
# Scenario 3: highest CPU → vm-004 at 78.5%

VMS = [
    {"vm_id": "vm-001", "name": "web-server-01",    "project_id": "project-alpha", "status": "running", "region": "us-east-1"},
    {"vm_id": "vm-002", "name": "db-server-01",     "project_id": "project-alpha", "status": "stopped", "region": "us-east-1"},
    {"vm_id": "vm-003", "name": "cache-server-01",  "project_id": "project-alpha", "status": "stopped", "region": "us-east-1"},
    {"vm_id": "vm-004", "name": "api-server-01",    "project_id": "project-beta",  "status": "running", "region": "us-west-2"},
    {"vm_id": "vm-005", "name": "worker-01",        "project_id": "project-beta",  "status": "stopped", "region": "us-west-2"},
    {"vm_id": "vm-006", "name": "ml-training-01",   "project_id": "project-beta",  "status": "stopped", "region": "us-west-2"},
    {"vm_id": "vm-007", "name": "frontend-01",      "project_id": "project-gamma", "status": "running", "region": "eu-west-1"},
    {"vm_id": "vm-008", "name": "backend-01",       "project_id": "project-gamma", "status": "running", "region": "eu-west-1"},
    {"vm_id": "vm-009", "name": "test-server-01",   "project_id": "project-gamma", "status": "stopped", "region": "eu-west-1"},
    {"vm_id": "vm-010", "name": "backup-server-01", "project_id": "project-gamma", "status": "stopped", "region": "eu-west-1"},
]

VM_ACTIVITY = {
    "vm-001": {"last_active": _ago(0)},
    "vm-002": {"last_active": _ago(15)},
    "vm-003": {"last_active": _ago(3)},
    "vm-004": {"last_active": _ago(0)},
    "vm-005": {"last_active": _ago(10)},
    "vm-006": {"last_active": _ago(20)},
    "vm-007": {"last_active": _ago(0)},
    "vm-008": {"last_active": _ago(0)},
    "vm-009": {"last_active": _ago(5)},
    "vm-010": {"last_active": _ago(30)},
}

VM_METRICS = {
    "vm-001": {"cpu_usage": 45.2, "memory_gb": 8},
    "vm-002": {"cpu_usage": 0.0,  "memory_gb": 16},
    "vm-003": {"cpu_usage": 0.0,  "memory_gb": 4},
    "vm-004": {"cpu_usage": 78.5, "memory_gb": 8},
    "vm-005": {"cpu_usage": 0.0,  "memory_gb": 4},
    "vm-006": {"cpu_usage": 0.0,  "memory_gb": 32},
    "vm-007": {"cpu_usage": 32.1, "memory_gb": 4},
    "vm-008": {"cpu_usage": 61.3, "memory_gb": 8},
    "vm-009": {"cpu_usage": 0.0,  "memory_gb": 4},
    "vm-010": {"cpu_usage": 0.0,  "memory_gb": 8},
}


def find_vm(vm_id: str):
    return next((v for v in VMS if v["vm_id"] == vm_id), None)

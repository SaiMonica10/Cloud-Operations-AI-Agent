from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from mock_api.data.synthetic import VMS, VM_ACTIVITY, find_vm

router = APIRouter(prefix="/vms", tags=["vms"])


def _days_inactive(last_active: str) -> int:
    last = datetime.strptime(last_active, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).days


@router.get("")
def list_vms(
    # Literal makes FastAPI reject unknown values with a 422 instead of silently returning []
    status: Literal["running", "stopped", "all"] = Query("all", description="Filter by status"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    result = list(VMS)
    if status != "all":
        result = [v for v in result if v["status"] == status]
    if project_id:
        result = [v for v in result if v["project_id"] == project_id]
    return result


@router.get("/{vm_id}/activity")
def get_vm_activity(vm_id: str):
    vm = find_vm(vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{vm_id}' not found")
    last_active = VM_ACTIVITY[vm_id]["last_active"]
    return {
        "vm_id": vm_id,
        "name": vm["name"],
        "status": vm["status"],
        "last_active": last_active,
        "days_inactive": _days_inactive(last_active),
    }

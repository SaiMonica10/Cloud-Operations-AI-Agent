from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from mock_api.data.synthetic import VMS
from datetime import datetime, timezone

router = APIRouter(prefix="/vms", tags=["vms"])

def _days_inactive(last_active: str) -> int:
    last = datetime.strptime(last_active, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).days

@router.get("")
def list_vms(
    status: str = Query("all", description="Filter by status: running, stopped, all"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    min_inactive_days: Optional[int] = Query(None, description="Only VMs inactive at least this many days"),
):
    result = [{**v, "days_inactive": _days_inactive(v["last_active"])} for v in VMS]
    if status != "all":
        result = [v for v in result if v["status"] == status]
    if project_id:
        result = [v for v in result if v["project_id"] == project_id]
    if min_inactive_days is not None:
        result = [v for v in result if v["days_inactive"] >= min_inactive_days]
    return result



@router.get("/{vm_id}/activity")
def get_vm_activity(vm_id: str):
    vm = next((v for v in VMS if v["vm_id"] == vm_id), None)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{vm_id}' not found")
    return {
        "vm_id": vm_id,
        "name": vm["name"],
        "status": vm["status"],
        "last_active": vm["last_active"],
    }

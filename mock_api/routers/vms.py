from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from mock_api.data.synthetic import VMS

router = APIRouter(prefix="/vms", tags=["vms"])


@router.get("")
def list_vms(
    status: str = Query("all", description="Filter by status: running, stopped, all"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    result = VMS
    if status != "all":
        result = [v for v in result if v["status"] == status]
    if project_id:
        result = [v for v in result if v["project_id"] == project_id]
    return result


@router.get("/{vm_id}")
def get_vm(vm_id: str):
    vm = next((v for v in VMS if v["vm_id"] == vm_id), None)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{vm_id}' not found")
    return vm


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

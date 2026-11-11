from fastapi import APIRouter, HTTPException
from mock_api.data.synthetic import VMS

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/{vm_id}")
def get_vm_metrics(vm_id: str):
    vm = next((v for v in VMS if v["vm_id"] == vm_id), None)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{vm_id}' not found")
    return {
        "vm_id": vm_id,
        "name": vm["name"],
        "status": vm["status"],
        "cpu_usage_percent": vm["cpu_usage"],
        "memory_gb": vm["memory_gb"],
    }

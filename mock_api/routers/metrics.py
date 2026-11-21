from fastapi import APIRouter, HTTPException
from mock_api.data.synthetic import VM_METRICS, find_vm

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/{vm_id}")
def get_vm_metrics(vm_id: str):
    vm = find_vm(vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{vm_id}' not found")
    metrics = VM_METRICS[vm_id]
    return {
        "vm_id": vm_id,
        "name": vm["name"],
        "status": vm["status"],
        "cpu_usage_percent": metrics["cpu_usage"],
        "memory_gb": metrics["memory_gb"],
    }

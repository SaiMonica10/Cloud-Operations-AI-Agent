from fastapi import APIRouter, HTTPException
from mock_api.data.synthetic import PROJECTS, VMS

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects():
    return PROJECTS


@router.get("/{project_id}")
def get_project(project_id: str):
    project = next((p for p in PROJECTS if p["project_id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return project


@router.get("/{project_id}/vms")
def list_project_vms(project_id: str):
    project = next((p for p in PROJECTS if p["project_id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return [v for v in VMS if v["project_id"] == project_id]

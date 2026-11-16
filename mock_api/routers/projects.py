from fastapi import APIRouter, HTTPException
from mock_api.data.synthetic import PROJECTS

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects():
    return PROJECTS

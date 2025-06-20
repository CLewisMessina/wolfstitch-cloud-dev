"""
Wolfstitch Cloud - Files API
Week 1 stub implementation
"""

from fastapi import APIRouter
from backend.models.schemas import APIResponse

router = APIRouter()


@router.get("/", response_model=APIResponse)
async def list_files():
    """List files endpoint (Week 1 stub)"""
    return APIResponse(
        message="File management will be enhanced in Week 2",
        data={"status": "basic_upload_available_in_processing"}
    )
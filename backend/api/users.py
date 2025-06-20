"""
Wolfstitch Cloud - Users API
Week 1 stub implementation
"""

from fastapi import APIRouter
from backend.models.schemas import APIResponse

router = APIRouter()


@router.get("/profile", response_model=APIResponse)
async def get_profile():
    """Get user profile (Week 1 stub)"""
    return APIResponse(
        message="User management will be implemented in Week 2",
        data={"status": "coming_soon"}
    )
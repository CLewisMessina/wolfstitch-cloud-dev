"""
Wolfstitch Cloud - Billing API
Week 1 stub implementation
"""

from fastapi import APIRouter
from backend.models.schemas import APIResponse

router = APIRouter()


@router.get("/subscription", response_model=APIResponse)
async def get_subscription():
    """Get subscription info (Week 1 stub)"""
    return APIResponse(
        message="Billing system will be implemented in Week 3",
        data={"status": "coming_soon"}
    )
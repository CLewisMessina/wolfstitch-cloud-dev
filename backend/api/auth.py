"""
Wolfstitch Cloud - Authentication API
Week 1 stub implementation
"""

from fastapi import APIRouter
from backend.models.schemas import APIResponse

router = APIRouter()


@router.post("/login", response_model=APIResponse)
async def login():
    """Login endpoint (Week 1 stub)"""
    return APIResponse(
        message="Authentication will be implemented in Week 2",
        data={"status": "coming_soon"}
    )


@router.post("/register", response_model=APIResponse)
async def register():
    """Register endpoint (Week 1 stub)"""
    return APIResponse(
        message="User registration will be implemented in Week 2",
        data={"status": "coming_soon"}
    )
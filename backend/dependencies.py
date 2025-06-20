"""
Wolfstitch Cloud - Dependencies
Simplified dependency injection for Week 1 implementation
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


class MockUser:
    """Mock user class for Week 1 development"""
    
    def __init__(self, user_id: str = "dev-user", tier: str = "pro"):
        self.user_id = user_id
        self.email = "dev@wolfstitch.com"
        self.tier = tier
        self.has_premium_features = tier in ["pro", "team", "enterprise"]


class MockRateLimiter:
    """Mock rate limiter for Week 1 development"""
    
    async def check_processing_limit(self, user):
        """Check processing rate limit for user"""
        # In Week 1, allow unlimited for development
        return True
    
    async def check_anonymous_limit(self):
        """Check anonymous processing limit"""
        # In Week 1, allow anonymous requests for testing
        return True
    
    async def check_anonymous_download_limit(self):
        """Check anonymous download limit"""
        return True


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> MockUser:
    """
    Get current user from JWT token
    For Week 1: Returns mock user for development
    """
    # For Week 1 development, return a mock user
    # In Week 2, we'll implement real JWT token validation
    
    if credentials and credentials.credentials:
        # Token provided - validate it (Week 2 implementation)
        logger.info(f"Token provided: {credentials.credentials[:20]}...")
        return MockUser(user_id="authenticated-user", tier="pro")
    else:
        # No token - return basic user for development
        return MockUser(user_id="dev-user", tier="free")


async def get_rate_limiter() -> MockRateLimiter:
    """
    Get rate limiter instance
    For Week 1: Returns mock limiter
    """
    return MockRateLimiter()


async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> MockUser:
    """
    Get authenticated user (requires token)
    For Week 1: Simplified validation
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # For Week 1, accept any token as valid
    # In Week 2, we'll validate JWT tokens properly
    return MockUser(user_id="authenticated-user", tier="pro")


# Optional dependencies (don't require authentication)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[MockUser]:
    """Get user if authenticated, None otherwise"""
    try:
        return await get_current_user(credentials)
    except:
        return None
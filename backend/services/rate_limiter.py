"""
Wolfstitch Cloud - Rate Limiter Service
Week 1 implementation with basic rate limiting
"""

import time
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """Basic rate limiter for Week 1"""
    
    def __init__(self):
        # In-memory storage for rate limiting (Week 1)
        # In production, this would use Redis
        self.requests: Dict[str, list] = {}
    
    async def check_processing_limit(self, user) -> bool:
        """Check processing rate limit for authenticated user"""
        # For Week 1, allow unlimited for development
        logger.info(f"Rate limit check for user {user.user_id}: OK")
        return True
    
    async def check_anonymous_limit(self) -> bool:
        """Check anonymous processing limit"""
        # For Week 1, allow anonymous requests for testing
        # In production, this would have stricter limits
        logger.info("Anonymous rate limit check: OK")
        return True
    
    async def check_anonymous_download_limit(self) -> bool:
        """Check anonymous download limit"""
        logger.info("Anonymous download rate limit check: OK")
        return True
    
    def _get_client_id(self, request) -> str:
        """Get client identifier for rate limiting"""
        # Simple implementation for Week 1
        return "anonymous"
    
    def _is_rate_limited(self, client_id: str, limit: int, window_minutes: int = 60) -> bool:
        """Check if client is rate limited"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        # Clean old requests
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > window_start
            ]
        else:
            self.requests[client_id] = []
        
        # Check if over limit
        if len(self.requests[client_id]) >= limit:
            return True
        
        # Add current request
        self.requests[client_id].append(now)
        return False


# Global rate limiter instance
rate_limiter = RateLimiter()
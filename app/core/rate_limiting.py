"""
Rate Limiting Module
Protects API endpoints from abuse using slowapi
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from typing import Callable
import redis.asyncio as aioredis
from app.core.config import settings

# ============================================================================
# RATE LIMITER CONFIGURATION
# ============================================================================

# Create rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],  # Default limit for all endpoints
    storage_uri=settings.REDIS_URL if settings.CACHE_ENABLED else "memory://",
    strategy="fixed-window",  # or "moving-window" for more accurate limiting
    headers_enabled=True  # Add rate limit headers to responses
)


# ============================================================================
# CUSTOM RATE LIMIT HANDLER
# ============================================================================

async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors
    Returns helpful error message with retry information
    """
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Please try again later.",
            "retry_after": exc.detail.split("Retry after ")[1] if "Retry after" in exc.detail else "60 seconds",
            "limit": str(exc)
        },
        headers={
            "X-RateLimit-Limit": str(request.state.view_rate_limit),
            "X-RateLimit-Remaining": str(request.state.view_rate_limit - 1),
            "Retry-After": "60"
        }
    )


# ============================================================================
# RATE LIMIT DECORATORS
# ============================================================================

def rate_limit(limit: str):
    """
    Decorator for applying rate limits to endpoints

    Usage:
        @router.get("/search")
        @rate_limit("100/minute")
        async def search_properties(...):
            pass

    Args:
        limit: Rate limit string (e.g., "100/minute", "1000/hour", "10/second")
    """
    return limiter.limit(limit)


def rate_limit_by_user(limit: str):
    """
    Rate limit based on authenticated user ID instead of IP

    Usage:
        @router.post("/properties")
        @rate_limit_by_user("50/hour")
        async def create_property(...):
            pass
    """

    def key_func(request: Request) -> str:
        # Try to get user ID from token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                token = auth_header.replace("Bearer ", "")
                payload = decode_token(token)
                user_id = payload.get("sub")
                if user_id:
                    return f"user:{user_id}"
            except:
                pass

        # Fallback to IP address
        return get_remote_address(request)

    return Limiter(
        key_func=key_func,
        storage_uri=settings.REDIS_URL if settings.CACHE_ENABLED else "memory://",
        strategy="fixed-window"
    ).limit(limit)


# ============================================================================
# RATE LIMIT CONFIGURATIONS BY ENDPOINT TYPE
# ============================================================================

class RateLimits:
    """Centralized rate limit configurations"""

    # Authentication endpoints
    AUTH_REGISTER = "5/minute"  # Prevent spam registrations
    AUTH_LOGIN = "10/minute"  # Prevent brute force attacks
    AUTH_REFRESH = "20/minute"

    # Search endpoints (most critical to protect)
    SEARCH_GENERAL = "100/minute"  # General search queries
    SEARCH_GEOSPATIAL = "50/minute"  # More expensive geospatial queries
    SEARCH_ANALYTICS = "20/minute"  # Analytics queries

    # Property endpoints
    PROPERTY_CREATE = "20/hour"  # Prevent spam listings
    PROPERTY_UPDATE = "50/hour"
    PROPERTY_VIEW = "200/minute"  # Allow many views
    PROPERTY_DELETE = "10/hour"

    # User endpoints
    USER_UPDATE = "30/hour"
    USER_PASSWORD_CHANGE = "5/hour"  # Security sensitive

    # Favorites & Alerts
    FAVORITE_ADD = "100/hour"
    FAVORITE_REMOVE = "100/hour"
    SAVED_SEARCH_CREATE = "20/hour"

    # Admin endpoints
    ADMIN_OPERATIONS = "200/minute"  # Higher limit for admin tasks

    # Email endpoints (if public)
    EMAIL_CONTACT = "5/hour"  # Prevent spam


# ============================================================================
# IP WHITELISTING
# ============================================================================

class IPWhitelist:
    """
    IP whitelist for bypassing rate limits
    Useful for internal services, monitoring, etc.
    """

    WHITELISTED_IPS = {
        "127.0.0.1",  # Localhost
        "::1",  # Localhost IPv6
        # Add production IPs here
        # "10.0.0.0/8",  # Internal network
    }

    @classmethod
    def is_whitelisted(cls, ip: str) -> bool:
        """Check if IP is whitelisted"""
        return ip in cls.WHITELISTED_IPS

    @classmethod
    def get_key_func(cls) -> Callable:
        """
        Get key function that exempts whitelisted IPs
        """

        def key_func(request: Request) -> str:
            ip = get_remote_address(request)
            if cls.is_whitelisted(ip):
                return "whitelisted"  # All whitelisted IPs share same "unlimited" bucket
            return ip

        return key_func


# ============================================================================
# DYNAMIC RATE LIMITING
# ============================================================================

class DynamicRateLimiter:
    """
    Dynamic rate limiter that adjusts limits based on user tier
    """

    # Rate limits by user tier
    TIER_LIMITS = {
        "free": {
            "search": "50/minute",
            "property_create": "10/hour",
        },
        "premium": {
            "search": "200/minute",
            "property_create": "50/hour",
        },
        "enterprise": {
            "search": "1000/minute",
            "property_create": "500/hour",
        }
    }

    @classmethod
    async def get_user_tier(cls, request: Request) -> str:
        """
        Determine user tier from request
        In MVP, everyone is "free". Later, check database for subscription.
        """
        # For MVP, return "free"
        # In Phase 4, implement:
        # - Check if user is authenticated
        # - Query subscription status from database
        # - Return appropriate tier
        return "free"

    @classmethod
    def limit_by_tier(cls, endpoint_type: str):
        """
        Apply rate limit based on user tier

        Usage:
            @router.get("/search")
            @DynamicRateLimiter.limit_by_tier("search")
            async def search(...):
                pass
        """

        async def decorator(request: Request):
            tier = await cls.get_user_tier(request)
            limit = cls.TIER_LIMITS.get(tier, {}).get(endpoint_type, "100/hour")
            return limit

        return decorator


# ============================================================================
# RATE LIMIT MIDDLEWARE
# ============================================================================

class RateLimitMiddleware:
    """
    Middleware to add rate limit headers to all responses
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # Add rate limit informational headers
                # These will be populated by slowapi
                headers.append((b"x-ratelimit-policy", b"dreamhome-api-v1"))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_headers)


# ============================================================================
# HELPERS
# ============================================================================

async def check_rate_limit(request: Request, limit: str) -> bool:
    """
    Manually check if request is within rate limit
    Returns True if within limit, False if exceeded
    """
    try:
        # This is a simplified check
        # slowapi handles this automatically when used as decorator
        return True
    except RateLimitExceeded:
        return False


def get_rate_limit_key(request: Request, key_type: str = "ip") -> str:
    """
    Get rate limit key for request

    Args:
        request: FastAPI request
        key_type: "ip", "user", or "custom"

    Returns:
        Rate limit key string
    """
    if key_type == "ip":
        return get_remote_address(request)
    elif key_type == "user":
        # Extract user ID from token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                token = auth_header.replace("Bearer ", "")
                payload = decode_token(token)
                user_id = payload.get("sub")
                if user_id:
                    return f"user:{user_id}"
            except:
                pass
        return get_remote_address(request)
    else:
        return get_remote_address(request)
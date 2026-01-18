"""
Custom Exception Classes and Handlers
Provides better error handling and consistent error responses
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import Any, Dict
from uuid import UUID
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTION CLASSES
# ============================================================================

class BaseAPIException(HTTPException):
    """Base exception class for all API exceptions"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        headers: Dict[str, Any] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or self.__class__.__name__


# ============================================================================
# PROPERTY EXCEPTIONS
# ============================================================================

class PropertyNotFoundException(BaseAPIException):
    """Raised when property is not found"""
    
    def __init__(self, property_id: UUID = None, slug: str = None):
        identifier = str(property_id) if property_id else slug
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {identifier} not found",
            error_code="PROPERTY_NOT_FOUND"
        )
        self.property_id = property_id
        self.slug = slug


class UnauthorizedPropertyAccessException(BaseAPIException):
    """Raised when user tries to access property they don't own"""
    
    def __init__(self, property_id: UUID, user_id: UUID):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this property",
            error_code="UNAUTHORIZED_PROPERTY_ACCESS"
        )
        self.property_id = property_id
        self.user_id = user_id


class PropertyValidationException(BaseAPIException):
    """Raised when property data is invalid"""
    
    def __init__(self, message: str, field: str = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
            error_code="PROPERTY_VALIDATION_ERROR"
        )
        self.field = field


class PropertyPublishException(BaseAPIException):
    """Raised when property cannot be published"""
    
    def __init__(self, reason: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish property: {reason}",
            error_code="PROPERTY_PUBLISH_ERROR"
        )


# ============================================================================
# USER EXCEPTIONS
# ============================================================================

class UserNotFoundException(BaseAPIException):
    """Raised when user is not found"""
    
    def __init__(self, user_id: UUID = None, email: str = None):
        identifier = str(user_id) if user_id else email
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {identifier} not found",
            error_code="USER_NOT_FOUND"
        )


class UserAlreadyExistsException(BaseAPIException):
    """Raised when trying to create user with existing email"""
    
    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {email} already exists",
            error_code="USER_ALREADY_EXISTS"
        )


class InvalidCredentialsException(BaseAPIException):
    """Raised when login credentials are invalid"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
            headers={"WWW-Authenticate": "Bearer"}
        )


class InactiveUserException(BaseAPIException):
    """Raised when user account is inactive"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
            error_code="INACTIVE_USER"
        )


class UnverifiedUserException(BaseAPIException):
    """Raised when user tries to access resource requiring verification"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email to access this resource.",
            error_code="UNVERIFIED_USER"
        )


# ============================================================================
# AUTHENTICATION EXCEPTIONS
# ============================================================================

class InvalidTokenException(BaseAPIException):
    """Raised when JWT token is invalid"""
    
    def __init__(self, reason: str = "Invalid or expired token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=reason,
            error_code="INVALID_TOKEN",
            headers={"WWW-Authenticate": "Bearer"}
        )


class TokenExpiredException(BaseAPIException):
    """Raised when JWT token has expired"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            error_code="TOKEN_EXPIRED",
            headers={"WWW-Authenticate": "Bearer"}
        )


class InsufficientPermissionsException(BaseAPIException):
    """Raised when user doesn't have required permissions"""
    
    def __init__(self, required_role: str = None):
        message = "Insufficient permissions to access this resource"
        if required_role:
            message += f". Required role: {required_role}"
        
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
            error_code="INSUFFICIENT_PERMISSIONS"
        )


# ============================================================================
# SEARCH EXCEPTIONS
# ============================================================================

class InvalidSearchQueryException(BaseAPIException):
    """Raised when search query is invalid"""
    
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search query: {message}",
            error_code="INVALID_SEARCH_QUERY"
        )


class SearchTimeoutException(BaseAPIException):
    """Raised when search query times out"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Search query timed out. Please try with more specific filters.",
            error_code="SEARCH_TIMEOUT"
        )


# ============================================================================
# FAVORITE EXCEPTIONS
# ============================================================================

class FavoriteAlreadyExistsException(BaseAPIException):
    """Raised when trying to add duplicate favorite"""
    
    def __init__(self, property_id: UUID):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Property already in favorites",
            error_code="FAVORITE_ALREADY_EXISTS"
        )


class FavoriteNotFoundException(BaseAPIException):
    """Raised when favorite is not found"""
    
    def __init__(self, property_id: UUID):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found",
            error_code="FAVORITE_NOT_FOUND"
        )


# ============================================================================
# SAVED SEARCH EXCEPTIONS
# ============================================================================

class SavedSearchLimitException(BaseAPIException):
    """Raised when user exceeds saved search limit"""
    
    def __init__(self, limit: int = 20):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum number of saved searches reached ({limit})",
            error_code="SAVED_SEARCH_LIMIT"
        )


class SavedSearchNotFoundException(BaseAPIException):
    """Raised when saved search is not found"""
    
    def __init__(self, search_id: UUID):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search {search_id} not found",
            error_code="SAVED_SEARCH_NOT_FOUND"
        )


# ============================================================================
# CACHE EXCEPTIONS
# ============================================================================

class CacheException(BaseAPIException):
    """Raised when cache operation fails"""
    
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache error: {message}",
            error_code="CACHE_ERROR"
        )


# ============================================================================
# DATABASE EXCEPTIONS
# ============================================================================

class DatabaseException(BaseAPIException):
    """Raised when database operation fails"""
    
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {message}",
            error_code="DATABASE_ERROR"
        )


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

async def base_api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """
    Handler for custom API exceptions
    Returns consistent error format
    """
    logger.error(
        f"API Exception: {exc.error_code} - {exc.detail}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        },
        headers=exc.headers
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for Pydantic validation errors
    Returns detailed field-level errors
    """
    logger.warning(
        f"Validation Error: {request.url.path}",
        extra={
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path,
                "details": exc.errors()
            }
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handler for standard HTTP exceptions
    """
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        },
        headers=getattr(exc, "headers", None)
    )


async def database_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for database-related exceptions
    """
    logger.error(
        f"Database Exception: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    # Integrity errors (unique constraints, foreign keys, etc.)
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "DATABASE_INTEGRITY_ERROR",
                    "message": "A database constraint was violated",
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": request.url.path
                }
            }
        )
    
    # Operational errors (connection issues, timeouts, etc.)
    if isinstance(exc, OperationalError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "Database is temporarily unavailable",
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": request.url.path
                }
            }
        )
    
    # Generic database error
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "An unexpected database error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for unhandled exceptions
    Logs detailed error and returns generic message to user
    """
    logger.critical(
        f"Unhandled Exception: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Our team has been notified.",
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        }
    )
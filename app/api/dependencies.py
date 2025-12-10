from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.services.user_service import user_service

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID from token
    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional check)

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        Current active user

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current verified user

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        Current verified user

    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email to access this resource."
        )
    return current_user


class RoleChecker:
    """Dependency class to check user roles"""

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """
        Check if user has required role

        Args:
            current_user: Current user from get_current_user dependency

        Returns:
            Current user if role is allowed

        Raises:
            HTTPException: If user doesn't have required role
        """
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource"
            )
        return current_user


# Pre-configured role checkers
require_admin = RoleChecker([UserRole.ADMIN])
require_agent = RoleChecker([UserRole.AGENT, UserRole.ADMIN])
require_owner = RoleChecker([UserRole.OWNER, UserRole.ADMIN])
require_agent_or_owner = RoleChecker([UserRole.AGENT, UserRole.OWNER, UserRole.ADMIN])
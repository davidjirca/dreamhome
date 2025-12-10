from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    PasswordChange,
    Message,
    UserPublicProfile
)
from app.services.user_service import user_service
from app.api.dependencies import get_current_user, get_current_active_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
        current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's profile

    Requires authentication
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
        user_data: UserUpdate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile

    - **first_name**: First name
    - **last_name**: Last name
    - **phone**: Phone number
    - **company_name**: Company name (for agents)
    - **license_number**: License number (for agents)

    Requires authentication
    """
    updated_user = await user_service.update_user(db, current_user.id, user_data)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return updated_user


@router.post("/me/change-password", response_model=Message)
async def change_password(
        password_data: PasswordChange,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Change current user's password

    - **current_password**: Current password for verification
    - **new_password**: New password (min 8 chars, must contain uppercase, lowercase, digit)
    - **new_password_confirm**: Must match new_password

    Requires authentication
    """
    await user_service.change_password(
        db,
        current_user.id,
        password_data.current_password,
        password_data.new_password
    )

    return Message(message="Password changed successfully")


@router.delete("/me", response_model=Message)
async def deactivate_account(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Deactivate current user's account (soft delete)

    Requires authentication
    """
    success = await user_service.deactivate_user(db, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to deactivate account"
        )

    return Message(message="Account deactivated successfully")


@router.get("/{user_id}/public", response_model=UserPublicProfile)
async def get_user_public_profile(
        user_id: UUID,
        db: AsyncSession = Depends(get_db)
):
    """
    Get public profile of any user by ID

    Returns limited public information (for displaying on listings, etc.)
    """
    user = await user_service.get_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user
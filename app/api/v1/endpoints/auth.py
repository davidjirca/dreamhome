from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    RefreshTokenRequest,
    Message
)
from app.services.user_service import user_service

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Register a new user

    - **email**: Valid email address
    - **password**: Minimum 8 characters, must contain uppercase, lowercase, and digit
    - **password_confirm**: Must match password
    - **role**: User role (buyer, owner, agent)
    - **first_name**: Optional first name
    - **last_name**: Optional last name
    - **phone**: Optional phone number
    """
    user = await user_service.create_user(db, user_data)
    return user


@router.post("/login", response_model=Token)
async def login(
        credentials: UserLogin,
        db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password

    Returns access token and refresh token
    """
    user = await user_service.authenticate(db, credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
        token_data: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token

    - **refresh_token**: Valid refresh token
    """
    # Decode refresh token
    payload = decode_token(token_data.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    from uuid import UUID
    try:
        user_id = UUID(user_id_str)
        user = await user_service.get_by_id(db, user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new tokens
    access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.post("/logout", response_model=Message)
async def logout():
    """
    Logout endpoint

    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token. This endpoint exists for consistency.

    For production, consider implementing a token blacklist using Redis.
    """
    return Message(message="Successfully logged out")
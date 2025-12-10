from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    """Service layer for user operations"""

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """
        Create a new user

        Args:
            db: Database session
            user_data: User creation data

        Returns:
            Created user object

        Raises:
            HTTPException: If email already exists
        """
        # Check if user already exists
        existing_user = await UserService.get_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        db_user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            role=user_data.role,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
        )

        try:
            db.add(db_user)
            await db.flush()
            await db.refresh(db_user)
            return db_user
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password

        Args:
            db: Database session
            email: User email
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = await UserService.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        await db.flush()

        return user

    @staticmethod
    async def update_user(
            db: AsyncSession,
            user_id: UUID,
            user_data: UserUpdate
    ) -> Optional[User]:
        """
        Update user profile

        Args:
            db: Database session
            user_id: User ID
            user_data: Update data

        Returns:
            Updated user object or None if not found
        """
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return None

        # Update only provided fields
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def change_password(
            db: AsyncSession,
            user_id: UUID,
            current_password: str,
            new_password: str
    ) -> bool:
        """
        Change user password

        Args:
            db: Database session
            user_id: User ID
            current_password: Current password (for verification)
            new_password: New password

        Returns:
            True if password changed successfully

        Raises:
            HTTPException: If current password is incorrect
        """
        user = await UserService.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )

        # Update password
        user.hashed_password = get_password_hash(new_password)
        await db.flush()
        return True

    @staticmethod
    async def deactivate_user(db: AsyncSession, user_id: UUID) -> bool:
        """
        Soft delete user (set deleted_at timestamp)

        Args:
            db: Database session
            user_id: User ID

        Returns:
            True if user deactivated successfully
        """
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return False

        user.deleted_at = datetime.utcnow()
        user.is_active = False
        await db.flush()
        return True

    @staticmethod
    async def verify_email(db: AsyncSession, user_id: UUID) -> bool:
        """
        Mark user email as verified

        Args:
            db: Database session
            user_id: User ID

        Returns:
            True if email verified successfully
        """
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return False

        user.is_verified = True
        await db.flush()
        return True

    @staticmethod
    async def verify_phone(db: AsyncSession, user_id: UUID) -> bool:
        """
        Mark user phone as verified

        Args:
            db: Database session
            user_id: User ID

        Returns:
            True if phone verified successfully
        """
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return False

        user.phone_verified = True
        await db.flush()
        return True


user_service = UserService()
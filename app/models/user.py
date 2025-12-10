from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    BUYER = "buyer"
    OWNER = "owner"
    AGENT = "agent"
    ADMIN = "admin"


class User(Base):
    """User model for authentication and profile"""
    __tablename__ = "users"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Role
    role = Column(SQLEnum(UserRole), default=UserRole.BUYER, nullable=False, index=True)

    # Profile Information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    phone_verified = Column(Boolean, default=False, nullable=False)

    # Agent/Owner specific
    company_name = Column(String(255), nullable=True)  # For agents
    license_number = Column(String(100), nullable=True)  # For agents

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split('@')[0]
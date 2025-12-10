from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.user import UserRole


# Base schemas
class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    role: UserRole = UserRole.BUYER
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


# Request schemas
class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, max_length=128)
    password_confirm: str = Field(..., min_length=8, max_length=128)

    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('password')
    def password_strength(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    license_number: Optional[str] = None


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    new_password_confirm: str = Field(..., min_length=8, max_length=128)

    @validator('new_password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


# Response schemas
class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    is_active: bool
    is_verified: bool
    phone_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    company_name: Optional[str] = None
    license_number: Optional[str] = None

    class Config:
        from_attributes = True


class UserPublicProfile(BaseModel):
    """Public user profile (for listings, etc.)"""
    id: UUID
    first_name: Optional[str]
    last_name: Optional[str]
    role: UserRole
    company_name: Optional[str] = None
    is_verified: bool
    phone_verified: bool

    class Config:
        from_attributes = True


# Token schemas
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh"""
    refresh_token: str


# Message schemas
class Message(BaseModel):
    """Generic message response"""
    message: str
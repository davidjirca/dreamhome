from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.saved_search import NotificationFrequency


class SavedSearchCreate(BaseModel):
    """Schema for creating a saved search"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    filters: Dict[str, Any] = Field(..., description="Search parameters from PropertySearchParams")
    email_notifications: bool = True
    notification_frequency: NotificationFrequency = NotificationFrequency.DAILY
    
    @validator('filters')
    def validate_filters(cls, v):
        if not v:
            raise ValueError('Filters cannot be empty')
        return v


class SavedSearchUpdate(BaseModel):
    """Schema for updating a saved search"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    filters: Optional[Dict[str, Any]] = None
    email_notifications: Optional[bool] = None
    notification_frequency: Optional[NotificationFrequency] = None
    is_active: Optional[bool] = None


class SavedSearchResponse(BaseModel):
    """Schema for saved search response"""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    filters: Dict[str, Any]
    email_notifications: bool
    notification_frequency: str
    last_notified_at: Optional[datetime]
    is_active: bool
    result_count: int
    last_checked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.alerts import AlertFrequency


# Saved Search Schemas
class SavedSearchBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name for this saved search")
    search_params: Dict[str, Any] = Field(..., description="Search parameters (PropertySearchParams)")
    alert_enabled: bool = Field(default=True, description="Enable alerts for this search")
    alert_frequency: AlertFrequency = Field(default=AlertFrequency.INSTANT, description="Alert frequency")
    alert_new_listings: bool = Field(default=True, description="Alert on new listings")
    alert_price_drops: bool = Field(default=True, description="Alert on price drops")


class SavedSearchCreate(SavedSearchBase):
    """Schema for creating a saved search"""
    pass


class SavedSearchUpdate(BaseModel):
    """Schema for updating a saved search"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    search_params: Optional[Dict[str, Any]] = None
    alert_enabled: Optional[bool] = None
    alert_frequency: Optional[AlertFrequency] = None
    alert_new_listings: Optional[bool] = None
    alert_price_drops: Optional[bool] = None


class SavedSearchResponse(SavedSearchBase):
    """Schema for saved search response"""
    id: UUID
    user_id: UUID
    last_alerted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Additional computed fields
    matching_count: Optional[int] = Field(None, description="Current count of matching properties")

    class Config:
        from_attributes = True


# Favorite Schemas
class FavoriteCreate(BaseModel):
    """Schema for adding a property to favorites"""
    property_id: UUID
    notes: Optional[str] = Field(None, max_length=500)


class FavoriteUpdate(BaseModel):
    """Schema for updating favorite notes"""
    notes: Optional[str] = Field(None, max_length=500)


class FavoriteResponse(BaseModel):
    """Schema for favorite response"""
    id: UUID
    user_id: UUID
    property_id: UUID
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FavoriteWithProperty(FavoriteResponse):
    """Schema for favorite with property details"""
    property: Dict[str, Any]  # PropertyListItem data


# Email Log Schemas
class EmailLogResponse(BaseModel):
    """Schema for email log response"""
    id: UUID
    user_id: Optional[UUID]
    email_to: str
    email_type: str
    subject: str
    sent_at: datetime
    success: bool
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


# Price History Schemas
class PriceHistoryResponse(BaseModel):
    """Schema for price history response"""
    id: UUID
    property_id: UUID
    old_price: float
    new_price: float
    price_change_percent: float
    changed_at: datetime

    class Config:
        from_attributes = True


# Alert Notification Schemas
class NewListingAlert(BaseModel):
    """Schema for new listing alert email data"""
    search_name: str
    properties: List[Dict[str, Any]]  # List of PropertyListItem
    search_url: str


class PriceDropAlert(BaseModel):
    """Schema for price drop alert email data"""
    property_id: UUID
    property_title: str
    old_price: float
    new_price: float
    price_drop_percent: float
    property_url: str
    main_photo: Optional[str]


class AlertDigest(BaseModel):
    """Schema for daily/weekly digest email"""
    frequency: AlertFrequency
    saved_searches: List[Dict[str, Any]]  # List of searches with new matches
    price_drops: List[PriceDropAlert]
    total_new_listings: int
    total_price_drops: int
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class FavoriteCreate(BaseModel):
    """Schema for adding property to favorites"""
    property_id: UUID
    notes: Optional[str] = Field(None, max_length=1000)


class FavoriteUpdate(BaseModel):
    """Schema for updating favorite notes"""
    notes: Optional[str] = Field(None, max_length=1000)


class FavoriteResponse(BaseModel):
    """Schema for favorite response"""
    id: UUID
    user_id: UUID
    property_id: UUID
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class FavoriteStats(BaseModel):
    """User's favorite statistics"""
    total_favorites: int
    for_sale: int
    for_rent: int
    avg_price: float
    cities: list[dict]  # [{"city": "Bucharest", "count": 5}]
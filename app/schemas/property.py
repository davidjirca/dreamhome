from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.models.property import PropertyType, PropertyStatus, ListingType


# Base schema
class PropertyBase(BaseModel):
    title: str = Field(..., min_length=10, max_length=200)
    description: Optional[str] = None
    property_type: PropertyType
    listing_type: ListingType
    price: Decimal = Field(..., gt=0)
    currency: str = "RON"
    negotiable: bool = False
    total_area: Decimal = Field(..., gt=0)
    usable_area: Optional[Decimal] = None
    rooms: int = Field(..., ge=1)
    bedrooms: int = Field(..., ge=0)
    bathrooms: int = Field(..., ge=1)
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    year_built: Optional[int] = None
    balconies: int = Field(default=0, ge=0)
    parking_spots: int = Field(default=0, ge=0)
    has_garage: bool = False
    has_terrace: bool = False
    has_garden: bool = False
    is_furnished: bool = False
    heating_type: Optional[str] = None
    energy_rating: Optional[str] = None
    address: str = Field(..., min_length=5)
    city: str
    county: str
    postal_code: Optional[str] = None
    neighborhood: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None


# Request schemas
class PropertyCreate(PropertyBase):
    """Schema for creating a property"""

    @validator('year_built')
    def validate_year(cls, v):
        if v and (v < 1800 or v > 2025):
            raise ValueError('Year built must be between 1800 and 2025')
        return v

    @validator('usable_area')
    def validate_usable_area(cls, v, values):
        if v and 'total_area' in values and v > values['total_area']:
            raise ValueError('Usable area cannot be greater than total area')
        return v


class PropertyUpdate(BaseModel):
    """Schema for updating a property"""
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    negotiable: Optional[bool] = None
    status: Optional[PropertyStatus] = None
    # ... add all optional fields


# Response schemas
class PropertyResponse(PropertyBase):
    """Full property response"""
    id: UUID
    owner_id: UUID
    status: PropertyStatus
    price_per_sqm: Optional[Decimal]
    photos: List[str]
    main_photo: Optional[str]
    photo_count: int
    slug: str
    view_count: int
    favorite_count: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class PropertyListItem(BaseModel):
    """Compact property for list views"""
    id: UUID
    title: str
    property_type: PropertyType
    listing_type: ListingType
    price: Decimal
    price_per_sqm: Optional[Decimal]
    total_area: Decimal
    rooms: int
    bedrooms: int
    city: str
    neighborhood: Optional[str]
    main_photo: Optional[str]
    slug: str
    created_at: datetime

    class Config:
        from_attributes = True


class PropertySearchParams(BaseModel):
    """Search parameters"""
    city: Optional[str] = None
    property_type: Optional[PropertyType] = None
    listing_type: Optional[ListingType] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    min_rooms: Optional[int] = None
    max_rooms: Optional[int] = None
    min_area: Optional[Decimal] = None
    max_area: Optional[Decimal] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="newest")


class PropertySearchResponse(BaseModel):
    """Paginated search results"""
    items: List[PropertyListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
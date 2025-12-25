from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.property import PropertyType, PropertyStatus, ListingType


# Base schema
class PropertyBase(BaseModel):
    title: str = Field(..., min_length=10, max_length=200)
    description: Optional[str] = None
    property_type: PropertyType
    listing_type: ListingType
    price: int = Field(..., gt=0, description="Price in EUR or RON (whole number)")
    currency: str = "RON"
    negotiable: bool = False
    total_area: int = Field(..., gt=0, description="Total area in square meters (whole number)")
    usable_area: Optional[int] = Field(None, gt=0, description="Usable area in square meters")
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
    latitude: Optional[float] = None  # Accept float from user, convert internally
    longitude: Optional[float] = None  # Accept float from user, convert internally


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
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be a positive integer')
        return v


class PropertyUpdate(BaseModel):
    """Schema for updating a property"""
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    negotiable: Optional[bool] = None
    status: Optional[PropertyStatus] = None
    total_area: Optional[int] = None
    usable_area: Optional[int] = None
    rooms: Optional[int] = Field(None, ge=1)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=1)
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    year_built: Optional[int] = None
    balconies: Optional[int] = Field(None, ge=0)
    parking_spots: Optional[int] = Field(None, ge=0)
    has_garage: Optional[bool] = None
    has_terrace: Optional[bool] = None
    has_garden: Optional[bool] = None
    is_furnished: Optional[bool] = None
    heating_type: Optional[str] = None
    energy_rating: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None
    neighborhood: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# Response schemas
class PropertyResponse(PropertyBase):
    """Full property response"""
    id: UUID
    owner_id: UUID
    status: PropertyStatus
    price_per_sqm: Optional[float]
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
    price: int
    price_per_sqm: Optional[float]
    total_area: int
    rooms: int
    bedrooms: int
    city: str
    neighborhood: Optional[str]
    main_photo: Optional[str]
    slug: str
    created_at: datetime
    parking_spots: int = 0
    has_garage: bool = False
    balconies: int = 0
    has_terrace: bool = False
    has_garden: bool = False
    is_furnished: bool = False

    # Additional fields for search results
    distance_km: Optional[float] = None  # Distance from search point
    relevance_score: Optional[float] = None  # Full-text search relevance
    days_online: Optional[int] = None  # Days since published

    class Config:
        from_attributes = True


class PropertySearchParams(BaseModel):
    """Enhanced search parameters with advanced filters"""

    # Text search
    search_text: Optional[str] = Field(None, max_length=500, description="Full-text search query")

    # Location filters
    cities: Optional[List[str]] = Field(None, description="List of cities to search in")
    city: Optional[str] = None  # Keep for backward compatibility
    county: Optional[str] = None
    neighborhood: Optional[str] = None

    # Geospatial filters
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[float] = Field(None, ge=0.1, le=50, description="Search radius in kilometers")

    # Bounding box (for map searches)
    ne_lat: Optional[float] = Field(None, ge=-90, le=90, description="Northeast latitude")
    ne_lng: Optional[float] = Field(None, ge=-180, le=180, description="Northeast longitude")
    sw_lat: Optional[float] = Field(None, ge=-90, le=90, description="Southwest latitude")
    sw_lng: Optional[float] = Field(None, ge=-180, le=180, description="Southwest longitude")

    # Property type filters
    property_type: Optional[PropertyType] = None
    listing_type: Optional[ListingType] = None

    # Price filters (integers)
    min_price: Optional[int] = Field(None, ge=0)
    max_price: Optional[int] = Field(None, ge=0)

    # Room filters
    min_rooms: Optional[int] = Field(None, ge=1)
    max_rooms: Optional[int] = Field(None, ge=1)
    min_bedrooms: Optional[int] = Field(None, ge=0)
    max_bedrooms: Optional[int] = Field(None, ge=0)
    min_bathrooms: Optional[int] = Field(None, ge=1)
    max_bathrooms: Optional[int] = Field(None, ge=1)

    # Area filters (integers)
    min_area: Optional[int] = Field(None, ge=0)
    max_area: Optional[int] = Field(None, ge=0)

    # Floor filters
    min_floor: Optional[int] = None
    max_floor: Optional[int] = None

    # Year built filters
    min_year_built: Optional[int] = Field(None, ge=1800, le=2025)
    max_year_built: Optional[int] = Field(None, ge=1800, le=2025)

    # Feature filters (boolean)
    has_parking: Optional[bool] = None
    has_garage: Optional[bool] = None
    has_balcony: Optional[bool] = None
    has_terrace: Optional[bool] = None
    has_garden: Optional[bool] = None
    is_furnished: Optional[bool] = None

    # Energy rating
    energy_rating: Optional[str] = None

    # Owner/Agent filter
    owner_id: Optional[UUID] = None

    # Time-based filters
    posted_since_days: Optional[int] = Field(None, ge=1, le=365, description="Posted in last N days")

    # Status filter
    exclude_sold_rented: bool = Field(True, description="Exclude sold/rented properties")

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    # Sorting
    sort_by: str = Field(
        default="newest",
        description="Sort by: newest, oldest, price_asc, price_desc, area_desc, distance, relevance"
    )

    @validator('max_price')
    def validate_price_range(cls, v, values):
        if v and 'min_price' in values and values['min_price'] and v < values['min_price']:
            raise ValueError('max_price must be greater than min_price')
        return v

    @validator('max_rooms')
    def validate_rooms_range(cls, v, values):
        if v and 'min_rooms' in values and values['min_rooms'] and v < values['min_rooms']:
            raise ValueError('max_rooms must be greater than min_rooms')
        return v

    @validator('max_area')
    def validate_area_range(cls, v, values):
        if v and 'min_area' in values and values['min_area'] and v < values['min_area']:
            raise ValueError('max_area must be greater than min_area')
        return v

    @validator('sort_by')
    def validate_sort(cls, v):
        valid_sorts = ['newest', 'oldest', 'price_asc', 'price_desc', 'area_desc', 'distance', 'relevance']
        if v not in valid_sorts:
            raise ValueError(f'sort_by must be one of: {", ".join(valid_sorts)}')
        return v


class PropertySearchResponse(BaseModel):
    """Paginated search results with metadata"""
    items: List[PropertyListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

    # Search metadata
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Active filters")
    search_time_ms: Optional[float] = Field(None, description="Query execution time")
    cached: bool = Field(False, description="Whether results came from cache")


class PopularSearch(BaseModel):
    """Popular search query"""
    search_text: str
    search_count: int
    last_searched: datetime


class SearchAnalytics(BaseModel):
    """Search analytics data"""
    total_searches: int
    unique_users: int
    avg_result_count: float
    avg_execution_time_ms: float
    popular_cities: List[Dict[str, Any]]
    popular_property_types: List[Dict[str, Any]]
    popular_price_ranges: List[Dict[str, Any]]
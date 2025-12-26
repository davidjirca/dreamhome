from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.user import UserRole
from app.models.property import PropertyStatus, PropertyType, ListingType


# ============================================================================
# USER MANAGEMENT SCHEMAS
# ============================================================================

class UserListItem(BaseModel):
    """Compact user info for admin list view"""
    id: UUID
    email: str
    role: UserRole
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    is_verified: bool
    phone_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    property_count: int = 0  # Number of properties owned
    
    class Config:
        from_attributes = True


class UserAdminDetail(BaseModel):
    """Detailed user info for admin view"""
    id: UUID
    email: str
    role: UserRole
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    is_active: bool
    is_verified: bool
    phone_verified: bool
    company_name: Optional[str]
    license_number: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    deleted_at: Optional[datetime]
    
    # Aggregated stats
    total_properties: int = 0
    active_properties: int = 0
    draft_properties: int = 0
    sold_properties: int = 0
    
    class Config:
        from_attributes = True


class UserSearchParams(BaseModel):
    """Parameters for searching users"""
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(
        default="created_desc",
        description="Sort by: created_desc, created_asc, email, last_login"
    )


class UserSearchResponse(BaseModel):
    """Paginated user search results"""
    items: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserModeration(BaseModel):
    """Actions for user moderation"""
    action: str = Field(..., description="activate, deactivate, verify, ban")
    reason: Optional[str] = Field(None, max_length=500)


# ============================================================================
# PROPERTY MODERATION SCHEMAS
# ============================================================================

class PropertyModerationItem(BaseModel):
    """Property info for moderation queue"""
    id: UUID
    title: str
    owner_id: UUID
    owner_email: str
    property_type: PropertyType
    listing_type: ListingType
    status: PropertyStatus
    price: float
    city: str
    neighborhood: Optional[str]
    main_photo: Optional[str]
    created_at: datetime
    published_at: Optional[datetime]
    view_count: int
    
    # Moderation flags
    reported_count: int = 0
    suspicious_score: float = 0.0
    
    class Config:
        from_attributes = True


class PropertyModerationAction(BaseModel):
    """Moderation action for property"""
    action: str = Field(..., description="approve, reject, flag, remove")
    reason: Optional[str] = Field(None, max_length=500)
    notify_owner: bool = True


class PropertyModerationQueue(BaseModel):
    """Moderation queue filters"""
    status: Optional[PropertyStatus] = None
    flagged_only: bool = False
    reported_only: bool = False
    created_after: Optional[datetime] = None
    
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ============================================================================
# ANALYTICS & DASHBOARD SCHEMAS
# ============================================================================

class PlatformStatistics(BaseModel):
    """Overall platform statistics"""
    # Users
    total_users: int
    active_users: int
    verified_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    
    # Properties
    total_properties: int
    active_listings: int
    draft_listings: int
    sold_listings: int
    expired_listings: int
    new_properties_today: int
    new_properties_this_week: int
    new_properties_this_month: int
    
    # Activity
    total_views_today: int
    total_views_this_week: int
    total_searches_today: int
    total_searches_this_week: int
    
    # Revenue (for future monetization)
    total_revenue: float = 0.0
    revenue_this_month: float = 0.0


class UserGrowthData(BaseModel):
    """User growth over time"""
    date: datetime
    new_users: int
    total_users: int
    active_users: int


class PropertyGrowthData(BaseModel):
    """Property growth over time"""
    date: datetime
    new_properties: int
    total_properties: int
    active_properties: int


class CityStatistics(BaseModel):
    """Statistics by city"""
    city: str
    property_count: int
    active_count: int
    avg_price: float
    total_views: int


class UserRoleDistribution(BaseModel):
    """Distribution of users by role"""
    role: UserRole
    count: int
    percentage: float


class PropertyTypeDistribution(BaseModel):
    """Distribution of properties by type"""
    property_type: PropertyType
    count: int
    percentage: float


class RecentActivity(BaseModel):
    """Recent platform activity"""
    activity_type: str  # "user_registration", "property_created", "property_sold", etc.
    description: str
    user_id: Optional[UUID]
    user_email: Optional[str]
    entity_id: Optional[UUID]  # Property ID, etc.
    timestamp: datetime


class DashboardMetrics(BaseModel):
    """Complete dashboard metrics"""
    statistics: PlatformStatistics
    user_growth: List[UserGrowthData]
    property_growth: List[PropertyGrowthData]
    top_cities: List[CityStatistics]
    user_role_distribution: List[UserRoleDistribution]
    property_type_distribution: List[PropertyTypeDistribution]
    recent_activity: List[RecentActivity]


# ============================================================================
# SYSTEM HEALTH SCHEMAS
# ============================================================================

class SystemHealth(BaseModel):
    """System health metrics"""
    database_status: str  # "healthy", "degraded", "down"
    cache_status: str
    api_status: str
    
    database_connections: int
    cache_hit_rate: float
    avg_response_time_ms: float
    
    disk_usage_percent: float
    memory_usage_percent: float
    
    total_api_calls_today: int
    failed_api_calls_today: int
    error_rate_percent: float


class AuditLog(BaseModel):
    """Audit log entry"""
    id: UUID
    admin_id: UUID
    admin_email: str
    action: str
    target_type: str  # "user", "property", "system"
    target_id: Optional[UUID]
    details: Dict[str, Any]
    ip_address: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# CONFIGURATION SCHEMAS
# ============================================================================

class PlatformSettings(BaseModel):
    """Platform configuration settings"""
    # Listing settings
    listing_expiry_days: int = 60
    max_photos_per_property: int = 20
    refresh_cooldown_hours: int = 24
    
    # Moderation settings
    auto_approve_verified_users: bool = False
    require_phone_verification: bool = False
    
    # Feature flags
    search_enabled: bool = True
    messaging_enabled: bool = False
    favorites_enabled: bool = True
    
    # Rate limits
    max_properties_per_user: int = 100
    max_searches_per_hour: int = 1000
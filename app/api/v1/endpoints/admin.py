from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
from math import ceil

from app.core.database import get_db
from app.models.user import User
from app.api.dependencies import get_current_user, require_admin
from app.services.admin_service import admin_service
from app.schemas.admin import (
    PlatformStatistics,
    DashboardMetrics,
    UserListItem,
    UserAdminDetail,
    UserSearchParams,
    UserSearchResponse,
    UserModeration,
    PropertyModerationItem,
    PropertyModerationAction,
    PropertyModerationQueue,
    CityStatistics,
    UserRoleDistribution,
    PropertyTypeDistribution,
    RecentActivity
)

router = APIRouter()


# ============================================================================
# DASHBOARD & ANALYTICS
# ============================================================================

@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    days: int = Query(30, ge=7, le=90, description="Historical data period in days"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **Admin Dashboard - Complete Overview**
    
    Get comprehensive platform metrics including:
    - Platform statistics (users, properties, activity)
    - User growth trends
    - Property growth trends
    - Top cities by activity
    - User role distribution
    - Property type distribution
    - Recent platform activity
    
    **Requires:** Admin role
    
    **Use Cases:**
    - Main admin dashboard
    - Platform monitoring
    - Business intelligence
    """
    
    # Get all metrics
    statistics = await admin_service.get_platform_statistics(db)
    user_growth = await admin_service.get_user_growth(db, days)
    property_growth = await admin_service.get_property_growth(db, days)
    top_cities = await admin_service.get_city_statistics(db, limit=10)
    user_roles = await admin_service.get_user_role_distribution(db)
    property_types = await admin_service.get_property_type_distribution(db)
    recent_activity = await admin_service.get_recent_activity(db, limit=20)
    
    return DashboardMetrics(
        statistics=statistics,
        user_growth=user_growth,
        property_growth=property_growth,
        top_cities=top_cities,
        user_role_distribution=user_roles,
        property_type_distribution=property_types,
        recent_activity=recent_activity
    )


@router.get("/statistics", response_model=PlatformStatistics)
async def get_platform_statistics(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **Platform Statistics Only**
    
    Get current platform statistics without historical data.
    Faster endpoint for quick stats checks.
    
    **Requires:** Admin role
    """
    return await admin_service.get_platform_statistics(db)


@router.get("/cities", response_model=List[CityStatistics])
async def get_city_statistics(
    limit: int = Query(10, ge=1, le=50, description="Number of cities to return"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **City Statistics**
    
    Get property statistics by city:
    - Property count
    - Active listings
    - Average price
    - Total views
    
    **Requires:** Admin role
    
    **Use Cases:**
    - Market analysis by location
    - Identify top markets
    - Regional performance
    """
    return await admin_service.get_city_statistics(db, limit)


@router.get("/activity", response_model=List[RecentActivity])
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Number of activities to return"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **Recent Platform Activity**
    
    Get recent user and property activities:
    - User registrations
    - Property listings
    - Status changes
    
    **Requires:** Admin role
    
    **Use Cases:**
    - Activity monitoring
    - Real-time dashboard updates
    - Audit trail
    """
    return await admin_service.get_recent_activity(db, limit)


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@router.post("/users/search", response_model=UserSearchResponse)
async def search_users(
    params: UserSearchParams,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **Search & Filter Users**
    
    Advanced user search with multiple filters:
    - Email search (partial match)
    - Filter by role
    - Filter by status (active/inactive)
    - Filter by verification status
    - Date range filters
    - Sorting options
    
    **Requires:** Admin role
    
    **Returns:** Paginated user list with property counts
    """
    
    users, total = await admin_service.search_users(
        db,
        email=params.email,
        role=params.role,
        is_active=params.is_active,
        is_verified=params.is_verified,
        created_after=params.created_after,
        created_before=params.created_before,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by
    )
    
    # Add property counts for each user
    user_items = []
    for user in users:
        # Count properties for this user
        from sqlalchemy import select, func
        from app.models.property import Property
        
        property_count_query = select(func.count(Property.id)).where(
            Property.owner_id == user.id,
            Property.deleted_at.is_(None)
        )
        property_count = (await db.execute(property_count_query)).scalar_one()
        
        user_items.append(UserListItem(
            id=user.id,
            email=user.email,
            role=user.role,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            phone_verified=user.phone_verified,
            created_at=user.created_at,
            last_login=user.last_login,
            property_count=property_count
        ))
    
    total_pages = ceil(total / params.page_size) if total > 0 else 0
    
    return UserSearchResponse(
        items=user_items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages
    )


@router.get("/users/{user_id}", response_model=UserAdminDetail)
async def get_user_details(
    user_id: UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **User Details**
    
    Get detailed information about a specific user:
    - Full profile data
    - Property statistics
    - Activity history
    
    **Requires:** Admin role
    """
    from sqlalchemy import select, func
    from app.models.property import Property, PropertyStatus
    
    # Get user
    user_query = select(User).where(User.id == user_id)
    user = (await db.execute(user_query)).scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get property statistics
    total_query = select(func.count(Property.id)).where(
        Property.owner_id == user_id,
        Property.deleted_at.is_(None)
    )
    total_properties = (await db.execute(total_query)).scalar_one()
    
    active_query = select(func.count(Property.id)).where(
        Property.owner_id == user_id,
        Property.status == PropertyStatus.ACTIVE,
        Property.deleted_at.is_(None)
    )
    active_properties = (await db.execute(active_query)).scalar_one()
    
    draft_query = select(func.count(Property.id)).where(
        Property.owner_id == user_id,
        Property.status == PropertyStatus.DRAFT,
        Property.deleted_at.is_(None)
    )
    draft_properties = (await db.execute(draft_query)).scalar_one()
    
    sold_query = select(func.count(Property.id)).where(
        Property.owner_id == user_id,
        Property.status.in_([PropertyStatus.SOLD, PropertyStatus.RENTED]),
        Property.deleted_at.is_(None)
    )
    sold_properties = (await db.execute(sold_query)).scalar_one()
    
    return UserAdminDetail(
        id=user.id,
        email=user.email,
        role=user.role,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        is_active=user.is_active,
        is_verified=user.is_verified,
        phone_verified=user.phone_verified,
        company_name=user.company_name,
        license_number=user.license_number,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        deleted_at=user.deleted_at,
        total_properties=total_properties,
        active_properties=active_properties,
        draft_properties=draft_properties,
        sold_properties=sold_properties
    )


@router.post("/users/{user_id}/moderate")
async def moderate_user(
    user_id: UUID,
    moderation: UserModeration,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **Moderate User Account**
    
    Perform moderation actions on user accounts:
    - **activate**: Reactivate user account
    - **deactivate**: Temporarily disable account
    - **verify**: Mark user as verified
    - **ban**: Permanently ban user (soft delete)
    
    **Requires:** Admin role
    
    **Actions are logged** for audit purposes.
    """
    
    user = await admin_service.moderate_user(
        db,
        user_id,
        moderation.action,
        current_admin.id,
        moderation.reason
    )
    
    await db.commit()
    
    return {
        "message": f"User {moderation.action}d successfully",
        "user_id": str(user_id),
        "action": moderation.action
    }


# ============================================================================
# PROPERTY MODERATION
# ============================================================================

@router.post("/properties/moderation-queue", response_model=List[PropertyModerationItem])
async def get_moderation_queue(
    params: PropertyModerationQueue,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **Property Moderation Queue**
    
    Get properties requiring moderation:
    - Filter by status
    - Flagged properties only
    - Reported properties only
    - Date filters
    
    **Requires:** Admin role
    
    **Use Cases:**
    - Review new listings
    - Handle reported content
    - Quality control
    """
    from sqlalchemy import select
    from app.models.property import Property
    
    # Build query
    query = select(Property, User).join(
        User, Property.owner_id == User.id
    ).where(
        Property.deleted_at.is_(None)
    )
    
    # Apply filters
    if params.status:
        query = query.where(Property.status == params.status)
    
    if params.created_after:
        query = query.where(Property.created_at >= params.created_after)
    
    # For now, we don't have flagged/reported fields
    # These would be added in Phase 2 with user reports
    
    # Pagination
    offset = (params.page - 1) * params.page_size
    query = query.order_by(Property.created_at.desc()).offset(offset).limit(params.page_size)
    
    result = await db.execute(query)
    properties = result.all()
    
    items = [
        PropertyModerationItem(
            id=prop.id,
            title=prop.title,
            owner_id=prop.owner_id,
            owner_email=owner.email,
            property_type=prop.property_type,
            listing_type=prop.listing_type,
            status=prop.status,
            price=float(prop.price),
            city=prop.city,
            neighborhood=prop.neighborhood,
            main_photo=prop.main_photo,
            created_at=prop.created_at,
            published_at=prop.published_at,
            view_count=prop.view_count,
            reported_count=0,  # TODO: Implement reporting system
            suspicious_score=0.0  # TODO: Implement spam detection
        )
        for prop, owner in properties
    ]
    
    return items


@router.post("/properties/{property_id}/moderate")
async def moderate_property(
    property_id: UUID,
    moderation: PropertyModerationAction,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **Moderate Property Listing**
    
    Perform moderation actions on properties:
    - **approve**: Approve and publish listing
    - **reject**: Reject and return to draft
    - **flag**: Mark for further review
    - **remove**: Remove listing (soft delete)
    
    **Requires:** Admin role
    
    **Options:**
    - Add reason for action
    - Notify property owner
    """
    
    property_obj = await admin_service.moderate_property(
        db,
        property_id,
        moderation.action,
        current_admin.id,
        moderation.reason
    )
    
    await db.commit()
    
    # TODO: Send notification to owner if notify_owner is True
    
    return {
        "message": f"Property {moderation.action}d successfully",
        "property_id": str(property_id),
        "action": moderation.action,
        "new_status": property_obj.status.value
    }


# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post("/users/bulk-action")
async def bulk_user_action(
    user_ids: List[UUID],
    action: str = Query(..., description="activate, deactivate, verify"),
    reason: str = Query(None, max_length=500),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **Bulk User Actions**
    
    Perform the same action on multiple users at once.
    
    **Requires:** Admin role
    
    **Actions:**
    - activate
    - deactivate
    - verify
    
    **Returns:** Count of successful operations
    """
    
    success_count = 0
    errors = []
    
    for user_id in user_ids:
        try:
            await admin_service.moderate_user(
                db,
                user_id,
                action,
                current_admin.id,
                reason
            )
            success_count += 1
        except Exception as e:
            errors.append({"user_id": str(user_id), "error": str(e)})
    
    await db.commit()
    
    return {
        "message": f"Bulk action completed",
        "action": action,
        "total_users": len(user_ids),
        "successful": success_count,
        "failed": len(errors),
        "errors": errors
    }


@router.post("/properties/bulk-action")
async def bulk_property_action(
    property_ids: List[UUID],
    action: str = Query(..., description="approve, reject, remove"),
    reason: str = Query(None, max_length=500),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **Bulk Property Actions**
    
    Perform the same action on multiple properties at once.
    
    **Requires:** Admin role
    
    **Actions:**
    - approve
    - reject
    - remove
    
    **Returns:** Count of successful operations
    """
    
    success_count = 0
    errors = []
    
    for property_id in property_ids:
        try:
            await admin_service.moderate_property(
                db,
                property_id,
                action,
                current_admin.id,
                reason
            )
            success_count += 1
        except Exception as e:
            errors.append({"property_id": str(property_id), "error": str(e)})
    
    await db.commit()
    
    return {
        "message": f"Bulk action completed",
        "action": action,
        "total_properties": len(property_ids),
        "successful": success_count,
        "failed": len(errors),
        "errors": errors
    }


# ============================================================================
# SYSTEM HEALTH
# ============================================================================

@router.get("/system/health")
async def get_system_health(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    **System Health Check**
    
    Get system health and performance metrics:
    - Database status
    - Cache status
    - API performance
    - Resource usage
    
    **Requires:** Admin role
    """
    from app.core.cache import cache_service
    
    # Database health
    try:
        await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = "down"
    
    # Cache health
    cache_status = "healthy" if cache_service.is_available() else "down"
    
    # Cache stats
    cache_stats = await cache_service.get_cache_stats() if cache_service.is_available() else {}
    
    return {
        "database_status": db_status,
        "cache_status": cache_status,
        "cache_stats": cache_stats,
        "api_status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
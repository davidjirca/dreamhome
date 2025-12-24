from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List
from math import ceil
import asyncio

from app.core.database import get_db
from app.models.user import User
from app.schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyListItem,
    PropertySearchParams,
    PropertySearchResponse,
    PopularSearch,
    SearchAnalytics
)
from app.services.property_service import property_service
from app.api.dependencies import get_current_user, require_agent_or_owner
from app.models.property import PropertyType, ListingType, PropertyStatus
from app.core.cache import cache_service
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta

router = APIRouter()


async def get_current_user_optional(
        request: Request,
        db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise
    Used for tracking search analytics
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        # Use the existing get_current_user dependency
        from app.api.dependencies import get_current_user
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=auth_header.replace("Bearer ", "")
        )

        return await get_current_user(credentials, db)
    except:
        return None


# ==========================================
# SPECIFIC ROUTES (MUST COME FIRST)
# ==========================================

@router.get("/search", response_model=PropertySearchResponse)
async def search_properties(
        request: Request,
        # TEXT SEARCH
        q: Optional[str] = Query(None, description="Full-text search query", max_length=500),

        # LOCATION FILTERS
        cities: Optional[str] = Query(None, description="Comma-separated city names"),
        city: Optional[str] = Query(None, description="Single city (legacy support)"),
        county: Optional[str] = None,
        neighborhood: Optional[str] = None,

        # GEOSPATIAL FILTERS
        lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for radius search"),
        lng: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for radius search"),
        radius: Optional[float] = Query(None, ge=0.1, le=50, description="Search radius in kilometers"),

        # BOUNDING BOX (for map searches)
        ne_lat: Optional[float] = Query(None, ge=-90, le=90, description="Northeast corner latitude"),
        ne_lng: Optional[float] = Query(None, ge=-180, le=180, description="Northeast corner longitude"),
        sw_lat: Optional[float] = Query(None, ge=-90, le=90, description="Southwest corner latitude"),
        sw_lng: Optional[float] = Query(None, ge=-180, le=180, description="Southwest corner longitude"),

        # PROPERTY TYPE FILTERS
        property_type: Optional[PropertyType] = None,
        listing_type: Optional[ListingType] = None,

        # PRICE FILTERS
        min_price: Optional[float] = Query(None, ge=0),
        max_price: Optional[float] = Query(None, ge=0),

        # ROOM FILTERS
        min_rooms: Optional[int] = Query(None, ge=1),
        max_rooms: Optional[int] = Query(None, ge=1),
        min_bedrooms: Optional[int] = Query(None, ge=0),
        max_bedrooms: Optional[int] = Query(None, ge=0),
        min_bathrooms: Optional[int] = Query(None, ge=1),
        max_bathrooms: Optional[int] = Query(None, ge=1),

        # AREA FILTERS
        min_area: Optional[float] = Query(None, ge=0),
        max_area: Optional[float] = Query(None, ge=0),

        # FLOOR FILTERS
        min_floor: Optional[int] = None,
        max_floor: Optional[int] = None,

        # YEAR BUILT FILTERS
        min_year_built: Optional[int] = Query(None, ge=1800, le=2025),
        max_year_built: Optional[int] = Query(None, ge=1800, le=2025),

        # FEATURE FILTERS
        has_parking: Optional[bool] = None,
        has_garage: Optional[bool] = None,
        has_balcony: Optional[bool] = None,
        has_terrace: Optional[bool] = None,
        has_garden: Optional[bool] = None,
        is_furnished: Optional[bool] = None,

        # ENERGY RATING
        energy_rating: Optional[str] = Query(None, description="Energy rating (A++, A+, A, B, C, D, E, F, G)"),

        # OWNER FILTER
        owner_id: Optional[UUID] = None,

        # TIME-BASED FILTERS
        posted_since: Optional[int] = Query(None, ge=1, le=365, description="Posted in last N days"),

        # STATUS FILTER
        exclude_sold_rented: bool = Query(True, description="Exclude sold/rented properties"),

        # PAGINATION
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Results per page"),

        # SORTING
        sort_by: str = Query(
            "newest",
            description="Sort by: newest, oldest, price_asc, price_desc, area_desc, distance, relevance"
        ),

        db: AsyncSession = Depends(get_db),
        current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    **Advanced Property Search with 30+ Filters**

    ## Search Types:

    ### 1. Full-Text Search
    - **q**: Search in title, description, neighborhood (Romanian language support)
    - Example: `q=apartament modern centru`

    ### 2. Location Search
    - **cities**: Multiple cities (comma-separated)
    - **county**: Filter by county
    - **neighborhood**: Filter by neighborhood
    - Example: `cities=Bucharest,Cluj-Napoca&neighborhood=Centru`

    ### 3. Geospatial Search
    - **Radius**: `lat=44.4268&lng=26.1025&radius=5` (5km radius)
    - **Bounding Box**: `ne_lat=44.5&ne_lng=26.2&sw_lat=44.3&sw_lng=25.9` (map viewport)

    ### 4. Property Filters
    - Type: apartment, house, studio, penthouse, villa, duplex, land, commercial
    - Listing: sale, rent
    - Price range, room count, area, floor, year built

    ### 5. Feature Filters
    - Boolean flags: parking, garage, balcony, terrace, garden, furnished

    ### 6. Sorting Options
    - **newest**: Recently published first
    - **oldest**: Oldest first
    - **price_asc**: Lowest price first
    - **price_desc**: Highest price first
    - **area_desc**: Largest area first
    - **distance**: Nearest first (requires lat/lng)
    - **relevance**: Most relevant first (requires text search)

    ## Performance:
    - Results cached for 5 minutes
    - Target: <100ms for complex queries
    - Supports 100+ concurrent users

    ## Response Includes:
    - Paginated results
    - Total count
    - Active filters
    - Execution time
    - Cache status
    """

    # Parse cities if provided as comma-separated string
    city_list = None
    if cities:
        city_list = [c.strip() for c in cities.split(',') if c.strip()]

    # Build search params
    params = PropertySearchParams(
        search_text=q,
        cities=city_list,
        city=city,
        county=county,
        neighborhood=neighborhood,
        latitude=lat,
        longitude=lng,
        radius_km=radius,
        ne_lat=ne_lat,
        ne_lng=ne_lng,
        sw_lat=sw_lat,
        sw_lng=sw_lng,
        property_type=property_type,
        listing_type=listing_type,
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        min_bedrooms=min_bedrooms,
        max_bedrooms=max_bedrooms,
        min_bathrooms=min_bathrooms,
        max_bathrooms=max_bathrooms,
        min_area=min_area,
        max_area=max_area,
        min_floor=min_floor,
        max_floor=max_floor,
        min_year_built=min_year_built,
        max_year_built=max_year_built,
        has_parking=has_parking,
        has_garage=has_garage,
        has_balcony=has_balcony,
        has_terrace=has_terrace,
        has_garden=has_garden,
        is_furnished=is_furnished,
        energy_rating=energy_rating,
        owner_id=owner_id,
        posted_since_days=posted_since,
        exclude_sold_rented=exclude_sold_rented,
        page=page,
        page_size=page_size,
        sort_by=sort_by
    )

    # Execute search
    properties, total, execution_time = await property_service.search_properties(
        db,
        params,
        current_user.id if current_user else None
    )

    # Track search analytics (async, don't block response)
    asyncio.create_task(
        property_service.track_search_query(
            db,
            params,
            total,
            execution_time,
            current_user.id if current_user else None,
            request.client.host if request.client else None,
            request.headers.get("user-agent")
        )
    )

    # Calculate total pages
    total_pages = ceil(total / page_size) if total > 0 else 0

    # Build response
    return PropertySearchResponse(
        items=[PropertyListItem.model_validate(prop) for prop in properties],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        filters_applied=params.model_dump(exclude_none=True),
        search_time_ms=round(execution_time, 2),
        cached=execution_time < 50  # Likely from cache if < 50ms
    )


@router.get("/search/popular", response_model=List[PopularSearch])
async def get_popular_searches(
        limit: int = Query(10, ge=1, le=50, description="Number of results"),
        days: int = Query(7, ge=1, le=30, description="Look back period in days"),
        db: AsyncSession = Depends(get_db)
):
    """
    Get most popular search queries

    **Features:**
    - Analyzes search_queries table
    - Returns top searches by frequency
    - Configurable time window

    **Use Cases:**
    - Show trending searches
    - Autocomplete suggestions
    - Market insights
    """
    from app.models.search_analytics import SearchQuery

    # Try cache first
    if cache_service.is_available():
        cached = await cache_service.get_popular_searches(limit)
        if cached:
            return cached

    # Calculate date cutoff
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Query popular searches
    query = select(
        SearchQuery.search_text,
        func.count(SearchQuery.id).label('search_count'),
        func.max(SearchQuery.created_at).label('last_searched')
    ).where(
        and_(
            SearchQuery.search_text.isnot(None),
            SearchQuery.created_at >= cutoff_date
        )
    ).group_by(
        SearchQuery.search_text
    ).order_by(
        desc('search_count')
    ).limit(limit)

    result = await db.execute(query)
    results = result.all()

    popular_searches = [
        PopularSearch(
            search_text=row.search_text,
            search_count=row.search_count,
            last_searched=row.last_searched
        )
        for row in results
    ]

    # Cache results for 1 hour
    if cache_service.is_available():
        await cache_service.set_popular_searches(
            [p.model_dump() for p in popular_searches],
            ttl=3600
        )

    return popular_searches


@router.get("/analytics/searches", response_model=SearchAnalytics)
async def get_search_analytics(
        days: int = Query(7, ge=1, le=90, description="Analysis period in days"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get search analytics data

    **Requires:** Authentication

    **Returns:**
    - Total searches
    - Unique users
    - Average result count
    - Average execution time
    - Popular cities
    - Popular property types
    - Popular price ranges

    **Use Cases:**
    - Platform analytics
    - Market insights
    - Performance monitoring
    """
    from app.models.search_analytics import SearchQuery

    # Calculate date cutoff
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Total searches
    total_query = select(func.count(SearchQuery.id)).where(
        SearchQuery.created_at >= cutoff_date
    )
    total_result = await db.execute(total_query)
    total_searches = total_result.scalar_one()

    # Unique users
    unique_users_query = select(func.count(func.distinct(SearchQuery.user_id))).where(
        and_(
            SearchQuery.created_at >= cutoff_date,
            SearchQuery.user_id.isnot(None)
        )
    )
    unique_users_result = await db.execute(unique_users_query)
    unique_users = unique_users_result.scalar_one()

    # Average result count
    avg_results_query = select(func.avg(SearchQuery.result_count)).where(
        SearchQuery.created_at >= cutoff_date
    )
    avg_results_result = await db.execute(avg_results_query)
    avg_result_count = float(avg_results_result.scalar_one() or 0)

    # Average execution time
    avg_time_query = select(func.avg(SearchQuery.execution_time_ms)).where(
        and_(
            SearchQuery.created_at >= cutoff_date,
            SearchQuery.execution_time_ms.isnot(None)
        )
    )
    avg_time_result = await db.execute(avg_time_query)
    avg_execution_time = float(avg_time_result.scalar_one() or 0)

    # TODO: Analyze filters JSON for popular cities, property types, price ranges
    # This requires JSONB queries which are more complex

    return SearchAnalytics(
        total_searches=total_searches,
        unique_users=unique_users,
        avg_result_count=avg_result_count,
        avg_execution_time_ms=avg_execution_time,
        popular_cities=[],  # TODO: Implement
        popular_property_types=[],  # TODO: Implement
        popular_price_ranges=[]  # TODO: Implement
    )


@router.get("/by-slug/{slug}", response_model=PropertyResponse)
async def get_property_by_slug(
        slug: str,
        db: AsyncSession = Depends(get_db)
):
    """
    Get property by URL-friendly slug

    **Example:** `/properties/by-slug/modern-apartment-bucharest-abc123de`
    """
    property_obj = await property_service.get_by_slug(db, slug)

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )

    # Increment view count
    property_obj.view_count += 1
    asyncio.create_task(db.flush())

    return property_obj


@router.post("/cache/invalidate", status_code=status.HTTP_204_NO_CONTENT)
async def invalidate_cache(
        current_user: User = Depends(get_current_user)
):
    """
    Manually invalidate search cache

    **Requires:** Authentication

    **Use Cases:**
    - Force cache refresh
    - After bulk property updates
    - Troubleshooting
    """
    await cache_service.invalidate_search_cache()
    return None


@router.get("/cache/stats")
async def get_cache_stats(
        current_user: User = Depends(get_current_user)
):
    """
    Get cache statistics

    **Requires:** Authentication

    **Returns:**
    - Cache enabled status
    - Total cached keys
    - Search cache keys
    - Property cache keys
    - Memory usage
    """
    stats = await cache_service.get_cache_stats()
    return stats


# ==========================================
# DYNAMIC PARAMETER ROUTES (MUST COME AFTER SPECIFIC ROUTES)
# ==========================================

@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
        property_data: PropertyCreate,
        current_user: User = Depends(require_agent_or_owner),
        db: AsyncSession = Depends(get_db)
):
    """
    Create new property listing

    Requires: Owner, Agent, or Admin role

    **Features:**
    - Automatic geocoding (if coordinates provided)
    - Slug generation
    - Price per sqm calculation
    - Cache invalidation
    """
    property_obj = await property_service.create_property(
        db,
        property_data,
        current_user.id
    )
    return property_obj


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
        property_id: UUID,
        db: AsyncSession = Depends(get_db)
):
    """
    Get property by ID

    **Features:**
    - Property caching (1 hour TTL)
    - Increments view count
    """
    property_obj = await property_service.get_by_id(db, property_id)

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )

    # Increment view count (async, don't block response)
    property_obj.view_count += 1
    asyncio.create_task(db.flush())

    return property_obj


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
        property_id: UUID,
        property_data: PropertyUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Update property listing

    **Features:**
    - Ownership verification
    - Cache invalidation (property + search)
    """
    property_obj = await property_service.update_property(
        db,
        property_id,
        property_data,
        current_user.id
    )

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )

    return property_obj


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
        property_id: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Soft delete property

    **Features:**
    - Ownership verification
    - Cache invalidation
    """
    success = await property_service.delete_property(
        db,
        property_id,
        current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )


@router.post("/{property_id}/publish", response_model=PropertyResponse)
async def publish_property(
        property_id: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Publish property listing

    **Validation:**
    - Requires at least one photo
    - Sets expiry date (60 days by default)

    **Features:**
    - Cache invalidation
    """
    property_obj = await property_service.publish_property(
        db,
        property_id,
        current_user.id
    )
    return property_obj


@router.post("/{property_id}/unpublish", response_model=PropertyResponse)
async def unpublish_property(
        property_id: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Unpublish property listing (set to inactive)

    **Features:**
    - Ownership verification
    - Cache invalidation
    """
    property_obj = await property_service.get_by_id(db, property_id)

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )

    # Check ownership
    if property_obj.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to unpublish this property"
        )

    # Update status
    property_obj.status = PropertyStatus.DRAFT
    await db.flush()
    await db.refresh(property_obj)

    # Invalidate cache
    await cache_service.invalidate_property(str(property_id))
    await cache_service.invalidate_search_cache()

    return property_obj
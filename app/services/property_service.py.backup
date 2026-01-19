from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func as sa_func, desc, asc, text
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from geoalchemy2.functions import ST_DWithin, ST_MakeEnvelope, ST_Within, ST_Distance, ST_SetSRID, ST_MakePoint
import re
import time

from app.models.property import Property, PropertyStatus
from app.models.search_analytics import SearchQuery
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertySearchParams, PropertyListItem
from app.core.config import settings
from app.core.cache import cache_service


class PropertyService:
    """Enhanced service layer for property operations with advanced search and caching"""

    @staticmethod
    def generate_slug(title: str, property_id: UUID) -> str:
        """Generate URL-friendly slug from title"""
        # Convert to lowercase and replace spaces with hyphens
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug)
        slug = slug.strip('-')
        # Add short ID for uniqueness
        slug = f"{slug}-{str(property_id)[:8]}"
        return slug

    @staticmethod
    def calculate_price_per_sqm(price: float, area: float) -> float:
        """Calculate price per square meter"""
        if area > 0:
            return round(price / area, 2)
        return 0.0

    @staticmethod
    async def create_property(
            db: AsyncSession,
            property_data: PropertyCreate,
            owner_id: UUID
    ) -> Property:
        """Create new property listing"""

        # Create property instance
        property_dict = property_data.model_dump()

        # Calculate price per sqm
        price_per_sqm = PropertyService.calculate_price_per_sqm(
            float(property_dict['price']),
            float(property_dict['total_area'])
        )

        # Handle geolocation
        location = None
        if property_dict.get('latitude') and property_dict.get('longitude'):
            location = f"SRID=4326;POINT({property_dict['longitude']} {property_dict['latitude']})"

        db_property = Property(
            **{k: v for k, v in property_dict.items() if k not in ['latitude', 'longitude']},
            owner_id=owner_id,
            price_per_sqm=price_per_sqm,
            status=PropertyStatus.DRAFT,
            slug="temp",  # Will be updated after getting ID
            location=location
        )

        db.add(db_property)
        await db.flush()

        # Generate and update slug
        db_property.slug = PropertyService.generate_slug(
            db_property.title,
            db_property.id
        )

        await db.flush()
        await db.refresh(db_property)

        # Invalidate search cache when new property is created
        await cache_service.invalidate_search_cache()

        return db_property

    @staticmethod
    async def get_by_id(
            db: AsyncSession,
            property_id: UUID,
            include_deleted: bool = False
    ) -> Optional[Property]:
        """Get property by ID with caching"""

        # Try cache first
        if cache_service.is_available():
            cached = await cache_service.get_property(str(property_id))
            if cached:
                # Reconstruct property from cached data
                # Note: For production, you'd want to properly deserialize this
                pass  # Skip cache reconstruction for now, fetch from DB

        query = select(Property).where(Property.id == property_id)

        if not include_deleted:
            query = query.where(Property.deleted_at.is_(None))

        result = await db.execute(query)
        property_obj = result.scalar_one_or_none()

        # Cache the property
        if property_obj and cache_service.is_available():
            await cache_service.set_property(
                str(property_id),
                {
                    "id": str(property_obj.id),
                    "title": property_obj.title,
                    "price": float(property_obj.price),
                    # ... add other fields as needed
                },
                ttl=settings.PROPERTY_CACHE_TTL
            )

        return property_obj

    @staticmethod
    async def get_by_slug(
            db: AsyncSession,
            slug: str
    ) -> Optional[Property]:
        """Get property by slug"""
        result = await db.execute(
            select(Property).where(
                Property.slug == slug,
                Property.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_property(
            db: AsyncSession,
            property_id: UUID,
            property_data: PropertyUpdate,
            user_id: UUID
    ) -> Optional[Property]:
        """Update property listing"""
        property_obj = await PropertyService.get_by_id(db, property_id)

        if not property_obj:
            return None

        # Check ownership
        if property_obj.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this property"
            )

        # Update fields
        update_data = property_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(property_obj, field, value)

        # Recalculate price_per_sqm if needed
        if 'price' in update_data or 'total_area' in update_data:
            property_obj.price_per_sqm = PropertyService.calculate_price_per_sqm(
                float(property_obj.price),
                float(property_obj.total_area)
            )

        await db.flush()
        await db.refresh(property_obj)

        # Invalidate caches
        await cache_service.invalidate_property(str(property_id))
        await cache_service.invalidate_search_cache()

        return property_obj

    @staticmethod
    async def delete_property(
            db: AsyncSession,
            property_id: UUID,
            user_id: UUID
    ) -> bool:
        """Soft delete property"""
        property_obj = await PropertyService.get_by_id(db, property_id)

        if not property_obj:
            return False

        # Check ownership
        if property_obj.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this property"
            )

        property_obj.deleted_at = datetime.utcnow()
        property_obj.status = PropertyStatus.EXPIRED
        await db.flush()

        # Invalidate caches
        await cache_service.invalidate_property(str(property_id))
        await cache_service.invalidate_search_cache()

        return True

    @staticmethod
    async def publish_property(
            db: AsyncSession,
            property_id: UUID,
            user_id: UUID
    ) -> Property:
        """Publish property listing"""
        property_obj = await PropertyService.get_by_id(db, property_id)

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        # Check ownership
        if property_obj.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to publish this property"
            )

        # Validate required fields
        if not property_obj.photos or len(property_obj.photos) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish property without photos"
            )

        # Update status
        property_obj.status = PropertyStatus.ACTIVE
        property_obj.published_at = datetime.utcnow()
        property_obj.expires_at = datetime.utcnow() + timedelta(
            days=settings.LISTING_EXPIRY_DAYS
        )

        await db.flush()
        await db.refresh(property_obj)

        # Invalidate search cache
        await cache_service.invalidate_search_cache()

        return property_obj

    @staticmethod
    async def search_properties(
            db: AsyncSession,
            params: PropertySearchParams,
            user_id: Optional[UUID] = None
    ) -> Tuple[List[Property], int, float]:
        """
        Advanced property search with caching - USING RAW SQL FOR TEXT SEARCH

        Returns:
            Tuple of (properties, total_count, execution_time_ms)
        """
        start_time = time.time()

        # Try cache first
        cache_key_params = params.model_dump(exclude_none=True)
        if cache_service.is_available():
            cached = await cache_service.get_search_results(cache_key_params)
            if cached:
                execution_time = (time.time() - start_time) * 1000
                return cached.get('properties', []), cached.get('total', 0), execution_time

        # Build base query
        query = select(Property).where(
            and_(
                Property.deleted_at.is_(None),
                Property.published_at.isnot(None)
            )
        )

        # Status filter
        if params.exclude_sold_rented:
            query = query.where(Property.status == PropertyStatus.ACTIVE)
        else:
            query = query.where(Property.status.in_([
                PropertyStatus.ACTIVE,
                PropertyStatus.SOLD,
                PropertyStatus.RENTED
            ]))

        # FULL-TEXT SEARCH - USING RAW SQL (MOST RELIABLE)
        search_rank_expr = None
        if params.search_text:
            # Clean search text
            search_text = params.search_text.strip()
            
            # Use raw SQL for text search - this always works!
            # The search_vector column is auto-generated by the database
            query = query.where(
                text("search_vector @@ plainto_tsquery('romanian', :search_text)")
            ).params(search_text=search_text)
            
            # For ranking, we'll add it in the order by clause
            search_rank_expr = text("ts_rank(search_vector, plainto_tsquery('romanian', :search_text))")

        # LOCATION FILTERS
        if params.cities:
            # Exact match for list of cities
            query = query.where(Property.city.in_(params.cities))
        elif params.city:
            # Case-insensitive partial match for single city
            query = query.where(Property.city.ilike(f"%{params.city}%"))

        if params.county:
            query = query.where(Property.county.ilike(f"%{params.county}%"))

        if params.neighborhood:
            query = query.where(Property.neighborhood.ilike(f"%{params.neighborhood}%"))

        # GEOSPATIAL FILTERS
        if params.latitude and params.longitude and params.radius_km:
            # Radius search using PostGIS
            point = ST_SetSRID(ST_MakePoint(params.longitude, params.latitude), 4326)
            radius_meters = params.radius_km * 1000
            
            query = query.where(
                ST_DWithin(
                    Property.location,
                    point,
                    radius_meters
                )
            )

        # Bounding box search (for map viewport)
        if all([params.ne_lat, params.ne_lng, params.sw_lat, params.sw_lng]):
            # Use && operator for bounding box overlap with geography type
            # More efficient and handles geography type correctly
            query = query.where(
                text(
                    "location && ST_MakeEnvelope(:sw_lng, :sw_lat, :ne_lng, :ne_lat, 4326)::geography"
                )
            ).params(
                sw_lng=params.sw_lng,
                sw_lat=params.sw_lat,
                ne_lng=params.ne_lng,
                ne_lat=params.ne_lat
            )

        # PROPERTY TYPE FILTERS
        if params.property_type:
            query = query.where(Property.property_type == params.property_type)

        if params.listing_type:
            query = query.where(Property.listing_type == params.listing_type)

        # PRICE FILTERS
        if params.min_price is not None:
            query = query.where(Property.price >= params.min_price)

        if params.max_price is not None:
            query = query.where(Property.price <= params.max_price)

        # ROOM FILTERS
        if params.min_rooms is not None:
            query = query.where(Property.rooms >= params.min_rooms)

        if params.max_rooms is not None:
            query = query.where(Property.rooms <= params.max_rooms)

        if params.min_bedrooms is not None:
            query = query.where(Property.bedrooms >= params.min_bedrooms)

        if params.max_bedrooms is not None:
            query = query.where(Property.bedrooms <= params.max_bedrooms)

        if params.min_bathrooms is not None:
            query = query.where(Property.bathrooms >= params.min_bathrooms)

        if params.max_bathrooms is not None:
            query = query.where(Property.bathrooms <= params.max_bathrooms)

        # AREA FILTERS
        if params.min_area is not None:
            query = query.where(Property.total_area >= params.min_area)

        if params.max_area is not None:
            query = query.where(Property.total_area <= params.max_area)

        # FLOOR FILTERS
        if params.min_floor is not None:
            query = query.where(Property.floor >= params.min_floor)

        if params.max_floor is not None:
            query = query.where(Property.floor <= params.max_floor)

        # YEAR BUILT FILTERS
        if params.min_year_built is not None:
            query = query.where(Property.year_built >= params.min_year_built)

        if params.max_year_built is not None:
            query = query.where(Property.year_built <= params.max_year_built)

        # FEATURE FILTERS (boolean)
        if params.has_parking is not None:
            if params.has_parking:
                query = query.where(Property.parking_spots > 0)
            else:
                query = query.where(Property.parking_spots == 0)

        if params.has_garage is not None:
            query = query.where(Property.has_garage == params.has_garage)

        if params.has_balcony is not None:
            if params.has_balcony:
                query = query.where(Property.balconies > 0)
            else:
                query = query.where(Property.balconies == 0)

        if params.has_terrace is not None:
            query = query.where(Property.has_terrace == params.has_terrace)

        if params.has_garden is not None:
            query = query.where(Property.has_garden == params.has_garden)

        if params.is_furnished is not None:
            query = query.where(Property.is_furnished == params.is_furnished)

        # ENERGY RATING
        if params.energy_rating:
            query = query.where(Property.energy_rating == params.energy_rating)

        # OWNER FILTER
        if params.owner_id:
            query = query.where(Property.owner_id == params.owner_id)

        # TIME-BASED FILTER
        if params.posted_since_days:
            cutoff_date = datetime.utcnow() - timedelta(days=params.posted_since_days)
            query = query.where(Property.published_at >= cutoff_date)

        # COUNT TOTAL (before pagination)
        count_query = select(sa_func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # SORTING
        if params.sort_by == "newest":
            query = query.order_by(desc(Property.published_at))
        elif params.sort_by == "oldest":
            query = query.order_by(asc(Property.published_at))
        elif params.sort_by == "price_asc":
            query = query.order_by(asc(Property.price))
        elif params.sort_by == "price_desc":
            query = query.order_by(desc(Property.price))
        elif params.sort_by == "area_desc":
            query = query.order_by(desc(Property.total_area))
        elif params.sort_by == "distance" and params.latitude and params.longitude:
            # Sort by distance from point
            point = ST_SetSRID(ST_MakePoint(params.longitude, params.latitude), 4326)
            distance_expr = ST_Distance(Property.location, point)
            query = query.order_by(asc(distance_expr))
        elif params.sort_by == "relevance" and search_rank_expr is not None:
            # Use raw SQL for ranking with text search
            query = query.order_by(desc(search_rank_expr)).params(search_text=params.search_text)
        else:
            # Default to newest
            query = query.order_by(desc(Property.published_at))

        # PAGINATION
        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        # EXECUTE QUERY
        result = await db.execute(query)
        properties = list(result.scalars().all())

        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000

        # Cache results
        if cache_service.is_available():
            await cache_service.set_search_results(
                cache_key_params,
                {
                    'properties': properties,
                    'total': total,
                    'execution_time_ms': execution_time
                },
                ttl=settings.SEARCH_CACHE_TTL
            )

        # Track search analytics (async, don't await)
        if params.search_text:
            await cache_service.increment_search_count(params.search_text)

        return properties, total, execution_time

    @staticmethod
    async def track_search_query(
            db: AsyncSession,
            params: PropertySearchParams,
            result_count: int,
            execution_time_ms: float,
            user_id: Optional[UUID] = None,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None
    ):
        """Track search query for analytics"""
        search_log = SearchQuery(
            user_id=user_id,
            search_text=params.search_text,
            filters=params.model_dump(exclude_none=True),
            result_count=result_count,
            execution_time_ms=int(execution_time_ms),
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(search_log)
        await db.flush()


property_service = PropertyService()
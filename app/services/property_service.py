from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from fastapi import HTTPException, status
import re

from app.models.property import Property, PropertyStatus
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertySearchParams
from app.core.config import settings


class PropertyService:
    """Service layer for property operations"""

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

        db_property = Property(
            **property_dict,
            owner_id=owner_id,
            price_per_sqm=price_per_sqm,
            status=PropertyStatus.DRAFT,
            slug="temp"  # Will be updated after getting ID
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
        return db_property

    @staticmethod
    async def get_by_id(
            db: AsyncSession,
            property_id: UUID,
            include_deleted: bool = False
    ) -> Optional[Property]:
        """Get property by ID"""
        query = select(Property).where(Property.id == property_id)

        if not include_deleted:
            query = query.where(Property.deleted_at.is_(None))

        result = await db.execute(query)
        return result.scalar_one_or_none()

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
        """Update property"""
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
        return property_obj

    @staticmethod
    async def search_properties(
            db: AsyncSession,
            params: PropertySearchParams
    ) -> tuple[List[Property], int]:
        """Search properties with filters and pagination"""

        # Base query - only active, published, non-deleted properties
        query = select(Property).where(
            and_(
                Property.status == PropertyStatus.ACTIVE,
                Property.deleted_at.is_(None),
                Property.published_at.isnot(None)
            )
        )

        # Apply filters
        if params.city:
            query = query.where(Property.city.ilike(f"%{params.city}%"))

        if params.property_type:
            query = query.where(Property.property_type == params.property_type)

        if params.listing_type:
            query = query.where(Property.listing_type == params.listing_type)

        if params.min_price:
            query = query.where(Property.price >= params.min_price)

        if params.max_price:
            query = query.where(Property.price <= params.max_price)

        if params.min_rooms:
            query = query.where(Property.rooms >= params.min_rooms)

        if params.max_rooms:
            query = query.where(Property.rooms <= params.max_rooms)

        if params.min_area:
            query = query.where(Property.total_area >= params.min_area)

        if params.max_area:
            query = query.where(Property.total_area <= params.max_area)

        # Count total
        from sqlalchemy import func as sa_func
        count_query = select(sa_func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Apply sorting
        if params.sort_by == "newest":
            query = query.order_by(Property.created_at.desc())
        elif params.sort_by == "price_asc":
            query = query.order_by(Property.price.asc())
        elif params.sort_by == "price_desc":
            query = query.order_by(Property.price.desc())
        elif params.sort_by == "area_desc":
            query = query.order_by(Property.total_area.desc())

        # Apply pagination
        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        # Execute query
        result = await db.execute(query)
        properties = result.scalars().all()

        return list(properties), total


property_service = PropertyService()
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from fastapi import HTTPException, status

from app.models.favorite import Favorite
from app.models.property import Property, ListingType
from app.schemas.favorite import FavoriteCreate, FavoriteUpdate


class FavoriteService:
    """Service layer for favorites operations"""
    
    @staticmethod
    async def add_favorite(
        db: AsyncSession,
        user_id: UUID,
        favorite_data: FavoriteCreate
    ) -> Favorite:
        """Add property to favorites"""
        
        # Check if property exists
        property_result = await db.execute(
            select(Property).where(
                Property.id == favorite_data.property_id,
                Property.deleted_at.is_(None)
            )
        )
        property_obj = property_result.scalar_one_or_none()
        
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        # Check if already favorited
        existing = await db.execute(
            select(Favorite).where(
                and_(
                    Favorite.user_id == user_id,
                    Favorite.property_id == favorite_data.property_id
                )
            )
        )
        
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Property already in favorites"
            )
        
        # Create favorite
        favorite = Favorite(
            user_id=user_id,
            property_id=favorite_data.property_id,
            notes=favorite_data.notes
        )
        
        db.add(favorite)
        
        # Increment favorite count on property
        property_obj.favorite_count += 1
        
        await db.flush()
        await db.refresh(favorite)
        
        return favorite
    
    @staticmethod
    async def remove_favorite(
        db: AsyncSession,
        user_id: UUID,
        property_id: UUID
    ) -> bool:
        """Remove property from favorites"""
        
        result = await db.execute(
            select(Favorite).where(
                and_(
                    Favorite.user_id == user_id,
                    Favorite.property_id == property_id
                )
            )
        )
        
        favorite = result.scalar_one_or_none()
        
        if not favorite:
            return False
        
        # Decrement favorite count on property
        property_result = await db.execute(
            select(Property).where(Property.id == property_id)
        )
        property_obj = property_result.scalar_one_or_none()
        
        if property_obj and property_obj.favorite_count > 0:
            property_obj.favorite_count -= 1
        
        await db.delete(favorite)
        await db.flush()
        
        return True
    
    @staticmethod
    async def update_favorite(
        db: AsyncSession,
        user_id: UUID,
        property_id: UUID,
        update_data: FavoriteUpdate
    ) -> Optional[Favorite]:
        """Update favorite notes"""
        
        result = await db.execute(
            select(Favorite).where(
                and_(
                    Favorite.user_id == user_id,
                    Favorite.property_id == property_id
                )
            )
        )
        
        favorite = result.scalar_one_or_none()
        
        if not favorite:
            return None
        
        if update_data.notes is not None:
            favorite.notes = update_data.notes
        
        await db.flush()
        await db.refresh(favorite)
        
        return favorite
    
    @staticmethod
    async def get_user_favorites(
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Favorite], int]:
        """Get user's favorites with pagination"""
        
        # Count total
        count_query = select(func.count()).select_from(
            select(Favorite).where(Favorite.user_id == user_id).subquery()
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get favorites
        query = select(Favorite).where(
            Favorite.user_id == user_id
        ).order_by(
            desc(Favorite.created_at)
        ).offset(skip).limit(limit)
        
        result = await db.execute(query)
        favorites = list(result.scalars().all())
        
        return favorites, total
    
    @staticmethod
    async def is_favorited(
        db: AsyncSession,
        user_id: UUID,
        property_id: UUID
    ) -> bool:
        """Check if property is favorited by user"""
        
        result = await db.execute(
            select(Favorite).where(
                and_(
                    Favorite.user_id == user_id,
                    Favorite.property_id == property_id
                )
            )
        )
        
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def get_favorites_stats(
        db: AsyncSession,
        user_id: UUID
    ) -> dict:
        """Get statistics about user's favorites"""
        
        query = select(
            func.count(Favorite.id).label('total'),
            func.count(Property.id).filter(Property.listing_type == ListingType.SALE).label('for_sale'),
            func.count(Property.id).filter(Property.listing_type == ListingType.RENT).label('for_rent'),
            func.avg(Property.price).label('avg_price')
        ).select_from(Favorite).join(
            Property, Favorite.property_id == Property.id
        ).where(
            and_(
                Favorite.user_id == user_id,
                Property.deleted_at.is_(None)
            )
        )
        
        result = await db.execute(query)
        stats = result.one()
        
        # Get cities breakdown
        cities_query = select(
            Property.city,
            func.count(Favorite.id).label('count')
        ).select_from(Favorite).join(
            Property, Favorite.property_id == Property.id
        ).where(
            and_(
                Favorite.user_id == user_id,
                Property.deleted_at.is_(None)
            )
        ).group_by(Property.city).order_by(desc('count')).limit(5)
        
        cities_result = await db.execute(cities_query)
        cities = [{"city": row.city, "count": row.count} for row in cities_result]
        
        return {
            "total_favorites": stats.total or 0,
            "for_sale": stats.for_sale or 0,
            "for_rent": stats.for_rent or 0,
            "avg_price": float(stats.avg_price or 0),
            "cities": cities
        }


favorite_service = FavoriteService()
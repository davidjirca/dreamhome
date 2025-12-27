from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from fastapi import HTTPException, status

from app.models.saved_search import SavedSearch
from app.schemas.saved_search import SavedSearchCreate, SavedSearchUpdate


class SavedSearchService:
    """Service layer for saved searches operations"""
    
    @staticmethod
    async def create_saved_search(
        db: AsyncSession,
        user_id: UUID,
        search_data: SavedSearchCreate
    ) -> SavedSearch:
        """Create a new saved search"""
        
        # Check user's saved search limit (max 20 per user for MVP)
        count_query = select(func.count()).where(SavedSearch.user_id == user_id)
        count_result = await db.execute(count_query)
        count = count_result.scalar_one()
        
        if count >= 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum number of saved searches reached (20)"
            )
        
        # Create saved search
        saved_search = SavedSearch(
            user_id=user_id,
            name=search_data.name,
            description=search_data.description,
            filters=search_data.filters,
            email_notifications=search_data.email_notifications,
            notification_frequency=search_data.notification_frequency
        )
        
        db.add(saved_search)
        await db.flush()
        await db.refresh(saved_search)
        
        return saved_search
    
    @staticmethod
    async def get_saved_search(
        db: AsyncSession,
        search_id: UUID,
        user_id: UUID
    ) -> Optional[SavedSearch]:
        """Get saved search by ID"""
        
        result = await db.execute(
            select(SavedSearch).where(
                and_(
                    SavedSearch.id == search_id,
                    SavedSearch.user_id == user_id
                )
            )
        )
        
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_saved_search(
        db: AsyncSession,
        search_id: UUID,
        user_id: UUID,
        update_data: SavedSearchUpdate
    ) -> Optional[SavedSearch]:
        """Update saved search"""
        
        saved_search = await SavedSearchService.get_saved_search(db, search_id, user_id)
        
        if not saved_search:
            return None
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(saved_search, field, value)
        
        await db.flush()
        await db.refresh(saved_search)
        
        return saved_search
    
    @staticmethod
    async def delete_saved_search(
        db: AsyncSession,
        search_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete saved search"""
        
        saved_search = await SavedSearchService.get_saved_search(db, search_id, user_id)
        
        if not saved_search:
            return False
        
        await db.delete(saved_search)
        await db.flush()
        
        return True
    
    @staticmethod
    async def get_user_saved_searches(
        db: AsyncSession,
        user_id: UUID,
        active_only: bool = True
    ) -> List[SavedSearch]:
        """Get all user's saved searches"""
        
        query = select(SavedSearch).where(SavedSearch.user_id == user_id)
        
        if active_only:
            query = query.where(SavedSearch.is_active == True)
        
        query = query.order_by(desc(SavedSearch.created_at))
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def execute_saved_search(
        db: AsyncSession,
        saved_search: SavedSearch
    ) -> Tuple[List, int]:
        """Execute a saved search and return results"""
        
        from app.services.property_service import property_service
        from app.schemas.property import PropertySearchParams
        
        # Convert saved filters to PropertySearchParams
        params = PropertySearchParams(**saved_search.filters)
        
        # Execute search
        properties, total, _ = await property_service.search_properties(
            db,
            params,
            user_id=saved_search.user_id
        )
        
        # Update last_checked_at and result_count
        saved_search.last_checked_at = datetime.utcnow()
        saved_search.result_count = total
        await db.flush()
        
        return properties, total
    
    @staticmethod
    async def get_saved_searches_for_notifications(
        db: AsyncSession,
        frequency: str
    ) -> List[SavedSearch]:
        """Get saved searches that need notifications"""
        
        now = datetime.utcnow()
        
        # Calculate cutoff time based on frequency
        if frequency == "immediate":
            cutoff = now - timedelta(minutes=15)
        elif frequency == "daily":
            cutoff = now - timedelta(days=1)
        elif frequency == "weekly":
            cutoff = now - timedelta(weeks=1)
        else:
            return []
        
        query = select(SavedSearch).where(
            and_(
                SavedSearch.is_active == True,
                SavedSearch.email_notifications == True,
                SavedSearch.notification_frequency == frequency,
                or_(
                    SavedSearch.last_notified_at.is_(None),
                    SavedSearch.last_notified_at < cutoff
                )
            )
        )
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def mark_as_notified(
        db: AsyncSession,
        search_id: UUID
    ):
        """Mark saved search as notified"""
        
        result = await db.execute(
            select(SavedSearch).where(SavedSearch.id == search_id)
        )
        
        saved_search = result.scalar_one_or_none()
        
        if saved_search:
            saved_search.last_notified_at = datetime.utcnow()
            await db.flush()


saved_search_service = SavedSearchService()
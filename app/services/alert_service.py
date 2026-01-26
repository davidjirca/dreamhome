from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func as sa_func
from fastapi import HTTPException, status

from app.models.saved_search import SavedSearch
from app.models.favorite import Favorite
from app.models.alerts import PropertyPriceHistory
from app.models.enums import NotificationFrequency
from app.models.property import Property, PropertyStatus
from app.models.user import User
from app.schemas.alerts import SavedSearchCreate, SavedSearchUpdate, FavoriteCreate
from app.services.property_service import property_service
from app.services.email_service import email_service
from app.core.config import settings

class AlertService:
    """Service layer for saved searches, favorites, and alerts"""
    
    # SAVED SEARCHES
    
    @staticmethod
    async def create_saved_search(
        db: AsyncSession,
        user_id: UUID,
        search_data: SavedSearchCreate
    ) -> SavedSearch:
        """Create a new saved search for a user"""
        
        # Check if user already has a saved search with this name
        existing = await db.execute(
            select(SavedSearch).where(
                and_(
                    SavedSearch.user_id == user_id,
                    SavedSearch.name == search_data.name
                )
            )
        )
        
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You already have a saved search named '{search_data.name}'"
            )
        
        # Create saved search
        saved_search = SavedSearch(
            user_id=user_id,
            name=search_data.name,
            search_params=search_data.search_params,
            alert_enabled=search_data.alert_enabled,
            alert_frequency=search_data.alert_frequency,
            alert_new_listings=search_data.alert_new_listings,
            alert_price_drops=search_data.alert_price_drops
        )
        
        db.add(saved_search)
        await db.flush()
        await db.refresh(saved_search)
        
        return saved_search
    
    @staticmethod
    async def get_user_saved_searches(
        db: AsyncSession,
        user_id: UUID
    ) -> List[SavedSearch]:
        """Get all saved searches for a user"""
        result = await db.execute(
            select(SavedSearch)
            .where(SavedSearch.user_id == user_id)
            .order_by(SavedSearch.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_saved_search_by_id(
        db: AsyncSession,
        search_id: UUID,
        user_id: UUID
    ) -> Optional[SavedSearch]:
        """Get a specific saved search"""
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
        search_data: SavedSearchUpdate
    ) -> Optional[SavedSearch]:
        """Update a saved search"""
        saved_search = await AlertService.get_saved_search_by_id(db, search_id, user_id)
        
        if not saved_search:
            return None
        
        # Update fields
        update_data = search_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
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
        """Delete a saved search"""
        saved_search = await AlertService.get_saved_search_by_id(db, search_id, user_id)
        
        if not saved_search:
            return False
        
        await db.delete(saved_search)
        await db.flush()
        
        return True
    
    @staticmethod
    async def get_matching_count(
        db: AsyncSession,
        search_params: dict
    ) -> int:
        """Get count of properties matching search parameters"""
        from app.schemas.property import PropertySearchParams
        
        # Convert dict to PropertySearchParams
        params = PropertySearchParams(**search_params)
        
        # Use property service to get count (reuse search logic)
        _, total, _ = await property_service.search_properties(db, params)
        
        return total
    
    # FAVORITES
    
    @staticmethod
    async def add_favorite(
        db: AsyncSession,
        user_id: UUID,
        favorite_data: FavoriteCreate
    ) -> Favorite:
        """Add a property to user's favorites"""
        
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Property already in favorites"
            )
        
        # Verify property exists
        property_exists = await db.execute(
            select(Property.id).where(Property.id == favorite_data.property_id)
        )
        
        if not property_exists.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        # Create favorite
        favorite = Favorite(
            user_id=user_id,
            property_id=favorite_data.property_id,
            notes=favorite_data.notes
        )
        
        db.add(favorite)
        
        # Increment favorite count on property
        await db.execute(
            select(Property)
            .where(Property.id == favorite_data.property_id)
        )
        property_obj = (await db.execute(
            select(Property).where(Property.id == favorite_data.property_id)
        )).scalar_one()
        property_obj.favorite_count += 1
        
        await db.flush()
        await db.refresh(favorite)
        
        return favorite
    
    @staticmethod
    async def get_user_favorites(
        db: AsyncSession,
        user_id: UUID,
        include_property_details: bool = True
    ) -> List[Favorite]:
        """Get all favorites for a user"""
        query = select(Favorite).where(Favorite.user_id == user_id)
        
        if include_property_details:
            from sqlalchemy.orm import selectinload
            query = query.options(selectinload(Favorite.property))
        
        result = await db.execute(query.order_by(Favorite.created_at.desc()))
        return list(result.scalars().all())
    
    @staticmethod
    async def remove_favorite(
        db: AsyncSession,
        user_id: UUID,
        property_id: UUID
    ) -> bool:
        """Remove a property from favorites"""
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
        property_obj = await db.execute(
            select(Property).where(Property.id == property_id)
        )
        prop = property_obj.scalar_one_or_none()
        if prop:
            prop.favorite_count = max(0, prop.favorite_count - 1)
        
        await db.delete(favorite)
        await db.flush()
        
        return True
    
    # PRICE TRACKING
    
    @staticmethod
    async def track_price_change(
        db: AsyncSession,
        property_id: UUID,
        old_price: int,
        new_price: int
    ):
        """Record a price change in history"""
        price_change_percent = ((new_price - old_price) / old_price) * 100
        
        price_history = PropertyPriceHistory(
            property_id=property_id,
            old_price=old_price,
            new_price=new_price,
            price_change_percent=price_change_percent
        )
        
        db.add(price_history)
        await db.flush()
        
        # If price dropped, send alerts to users who favorited this property
        if new_price < old_price:
            await AlertService._send_price_drop_alerts(
                db, property_id, old_price, new_price, price_change_percent
            )
    
    @staticmethod
    async def _send_price_drop_alerts(
        db: AsyncSession,
        property_id: UUID,
        old_price: int,
        new_price: int,
        price_drop_percent: float
    ):
        """Send price drop alerts to users who favorited this property"""
        
        # Get property details
        property_obj = await property_service.get_by_id(db, property_id)
        if not property_obj:
            return
        
        # Get users who favorited this property
        result = await db.execute(
            select(Favorite).where(Favorite.property_id == property_id)
        )
        favorites = result.scalars().all()
        
        # Send email to each user
        for favorite in favorites:
            # Get user
            user_result = await db.execute(
                select(User).where(User.id == favorite.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user and user.is_active:
                property_url = f"{settings.PLATFORM_URL}/properties/{property_obj.slug}"
                
                await email_service.send_price_drop_alert(
                    to_email=user.email,
                    user_id=user.id,
                    property_title=property_obj.title,
                    old_price=float(old_price),
                    new_price=float(new_price),
                    price_drop_percent=price_drop_percent,
                    property_url=property_url,
                    main_photo=property_obj.main_photo,
                    db=db
                )
    
    # ALERT PROCESSING
    
    @staticmethod
    async def check_and_send_instant_alerts(
        db: AsyncSession,
        property_id: UUID
    ):
        """
        Check if new property matches any saved searches and send instant alerts
        
        Called when a new property is published
        """
        
        # Get property details
        property_obj = await property_service.get_by_id(db, property_id)
        if not property_obj or property_obj.status != PropertyStatus.ACTIVE:
            return
        
        # Get all saved searches with instant alerts enabled
        result = await db.execute(
            select(SavedSearch).where(
                and_(
                    SavedSearch.alert_enabled == True,
                    SavedSearch.alert_frequency.in_([
                        NotificationFrequency.INSTANT,
                        NotificationFrequency.IMMEDIATE
                    ]),
                    SavedSearch.alert_new_listings == True
                )
            )
        )
        saved_searches = result.scalars().all()
        
        # Check each saved search
        for saved_search in saved_searches:
            # Check if property matches search criteria
            if await AlertService._property_matches_search(property_obj, saved_search.search_params):
                # Send alert
                await AlertService._send_new_listing_alert(
                    db, saved_search, [property_obj]
                )
                
                # Update last alerted timestamp
                saved_search.last_alerted_at = datetime.utcnow()
                await db.flush()
    
    @staticmethod
    async def _property_matches_search(
        property_obj: Property,
        search_params: dict
    ) -> bool:
        """Check if a property matches saved search criteria"""
        from app.schemas.property import PropertySearchParams
        
        # Convert to search params
        params = PropertySearchParams(**search_params)
        
        # Check basic filters
        if params.cities and property_obj.city not in params.cities:
            return False
        
        if params.city and params.city.lower() not in property_obj.city.lower():
            return False
        
        if params.property_type and property_obj.property_type != params.property_type:
            return False
        
        if params.listing_type and property_obj.listing_type != params.listing_type:
            return False
        
        if params.min_price and property_obj.price < params.min_price:
            return False
        
        if params.max_price and property_obj.price > params.max_price:
            return False
        
        if params.min_rooms and property_obj.rooms < params.min_rooms:
            return False
        
        if params.max_rooms and property_obj.rooms > params.max_rooms:
            return False
        
        # Add more filters as needed...
        
        return True
    
    @staticmethod
    async def _send_new_listing_alert(
        db: AsyncSession,
        saved_search: SavedSearch,
        properties: List[Property]
    ):
        """Send new listing alert email"""
        
        # Get user
        user_result = await db.execute(
            select(User).where(User.id == saved_search.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return
        
        # Prepare property data for email
        property_data = []
        for prop in properties:
            property_data.append({
                'id': str(prop.id),
                'title': prop.title,
                'price': float(prop.price),
                'city': prop.city,
                'rooms': prop.rooms,
                'total_area': float(prop.total_area),
                'main_photo': prop.main_photo,
                'url': f"{settings.PLATFORM_URL}/properties/{prop.slug}"
            })
        
        search_url = f"{settings.PLATFORM_URL}/search?saved_search={saved_search.id}"
        
        await email_service.send_new_listing_alert(
            to_email=user.email,
            user_id=user.id,
            search_name=saved_search.name,
            properties=property_data,
            search_url=search_url,
            db=db
        )
    
    @staticmethod
    async def process_daily_digests(db: AsyncSession):
        """
        Process and send daily digest emails
        
        Should be run once per day via cron job or scheduler
        """
        
        # Get all saved searches with daily frequency
        result = await db.execute(
            select(SavedSearch).where(
                and_(
                    SavedSearch.alert_enabled == True,
                    SavedSearch.alert_frequency == NotificationFrequency.DAILY
                )
            )
        )
        saved_searches = result.scalars().all()
        
        # Group by user
        user_searches = {}
        for search in saved_searches:
            if search.user_id not in user_searches:
                user_searches[search.user_id] = []
            user_searches[search.user_id].append(search)
        
        # Process each user
        for user_id, searches in user_searches.items():
            await AlertService._send_daily_digest_for_user(db, user_id, searches)
    
    @staticmethod
    async def _send_daily_digest_for_user(
        db: AsyncSession,
        user_id: UUID,
        saved_searches: List[SavedSearch]
    ):
        """Send daily digest for a specific user"""
        
        # Get user
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return
        
        # Get new listings for each saved search (since last alert)
        searches_with_new = []
        cutoff = datetime.utcnow() - timedelta(days=1)
        
        for search in saved_searches:
            # Get matching properties published since cutoff
            from app.schemas.property import PropertySearchParams
            params = PropertySearchParams(**search.search_params)
            params.posted_since_days = 1
            
            properties, total, _ = await property_service.search_properties(db, params)
            
            if total > 0:
                searches_with_new.append({
                    'name': search.name,
                    'new_count': total,
                    'properties': properties[:5],  # First 5 properties
                    'url': f"{settings.PLATFORM_URL}/search?saved_search={search.id}"
                })
                
                # Update last alerted
                search.last_alerted_at = datetime.utcnow()
        
        # Get price drops on favorited properties
        price_drops = await AlertService._get_recent_price_drops_for_user(db, user_id, cutoff)
        
        # Send digest if there's anything new
        if searches_with_new or price_drops:
            await email_service.send_daily_digest(
                to_email=user.email,
                user_id=user.id,
                saved_searches_with_new=searches_with_new,
                price_drops=price_drops,
                db=db
            )
            
            await db.flush()
    
    @staticmethod
    async def _get_recent_price_drops_for_user(
        db: AsyncSession,
        user_id: UUID,
        since: datetime
    ) -> List[dict]:
        """Get recent price drops for properties user has favorited"""
        
        # Get user's favorites
        favorites_result = await db.execute(
            select(Favorite.property_id).where(Favorite.user_id == user_id)
        )
        favorited_property_ids = [row[0] for row in favorites_result.all()]
        
        if not favorited_property_ids:
            return []
        
        # Get price drops for these properties
        result = await db.execute(
            select(PropertyPriceHistory)
            .where(
                and_(
                    PropertyPriceHistory.property_id.in_(favorited_property_ids),
                    PropertyPriceHistory.changed_at >= since,
                    PropertyPriceHistory.price_change_percent < 0  # Price drops only
                )
            )
            .order_by(PropertyPriceHistory.changed_at.desc())
        )
        price_histories = result.scalars().all()
        
        # Format for email
        price_drops = []
        for history in price_histories:
            property_obj = await property_service.get_by_id(db, history.property_id)
            if property_obj:
                price_drops.append({
                    'property_title': property_obj.title,
                    'old_price': float(history.old_price),
                    'new_price': float(history.new_price),
                    'price_drop_percent': abs(float(history.price_change_percent)),
                    'property_url': f"{settings.PLATFORM_URL}/properties/{property_obj.slug}",
                    'main_photo': property_obj.main_photo
                })
        
        return price_drops


alert_service = AlertService()
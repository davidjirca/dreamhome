from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, case
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.property import Property, PropertyStatus, PropertyType
from app.models.search_analytics import SearchQuery
from app.schemas.admin import (
    PlatformStatistics,
    UserGrowthData,
    PropertyGrowthData,
    CityStatistics,
    UserRoleDistribution,
    PropertyTypeDistribution,
    RecentActivity
)


class AdminService:
    """Service layer for admin operations"""
    
    @staticmethod
    async def get_platform_statistics(db: AsyncSession) -> PlatformStatistics:
        """Get overall platform statistics"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        # User statistics
        total_users_query = select(func.count(User.id)).where(User.deleted_at.is_(None))
        total_users = (await db.execute(total_users_query)).scalar_one()
        
        active_users_query = select(func.count(User.id)).where(
            and_(User.deleted_at.is_(None), User.is_active == True)
        )
        active_users = (await db.execute(active_users_query)).scalar_one()
        
        verified_users_query = select(func.count(User.id)).where(
            and_(User.deleted_at.is_(None), User.is_verified == True)
        )
        verified_users = (await db.execute(verified_users_query)).scalar_one()
        
        new_users_today_query = select(func.count(User.id)).where(
            and_(User.deleted_at.is_(None), User.created_at >= today_start)
        )
        new_users_today = (await db.execute(new_users_today_query)).scalar_one()
        
        new_users_week_query = select(func.count(User.id)).where(
            and_(User.deleted_at.is_(None), User.created_at >= week_start)
        )
        new_users_this_week = (await db.execute(new_users_week_query)).scalar_one()
        
        new_users_month_query = select(func.count(User.id)).where(
            and_(User.deleted_at.is_(None), User.created_at >= month_start)
        )
        new_users_this_month = (await db.execute(new_users_month_query)).scalar_one()
        
        # Property statistics
        total_properties_query = select(func.count(Property.id)).where(Property.deleted_at.is_(None))
        total_properties = (await db.execute(total_properties_query)).scalar_one()
        
        active_listings_query = select(func.count(Property.id)).where(
            and_(Property.deleted_at.is_(None), Property.status == PropertyStatus.ACTIVE)
        )
        active_listings = (await db.execute(active_listings_query)).scalar_one()
        
        draft_listings_query = select(func.count(Property.id)).where(
            and_(Property.deleted_at.is_(None), Property.status == PropertyStatus.DRAFT)
        )
        draft_listings = (await db.execute(draft_listings_query)).scalar_one()
        
        sold_listings_query = select(func.count(Property.id)).where(
            and_(Property.deleted_at.is_(None), Property.status.in_([PropertyStatus.SOLD, PropertyStatus.RENTED]))
        )
        sold_listings = (await db.execute(sold_listings_query)).scalar_one()
        
        expired_listings_query = select(func.count(Property.id)).where(
            and_(Property.deleted_at.is_(None), Property.status == PropertyStatus.EXPIRED)
        )
        expired_listings = (await db.execute(expired_listings_query)).scalar_one()
        
        new_properties_today_query = select(func.count(Property.id)).where(
            and_(Property.deleted_at.is_(None), Property.created_at >= today_start)
        )
        new_properties_today = (await db.execute(new_properties_today_query)).scalar_one()
        
        new_properties_week_query = select(func.count(Property.id)).where(
            and_(Property.deleted_at.is_(None), Property.created_at >= week_start)
        )
        new_properties_this_week = (await db.execute(new_properties_week_query)).scalar_one()
        
        new_properties_month_query = select(func.count(Property.id)).where(
            and_(Property.deleted_at.is_(None), Property.created_at >= month_start)
        )
        new_properties_this_month = (await db.execute(new_properties_month_query)).scalar_one()
        
        # Activity statistics
        total_views_today_query = select(func.sum(Property.view_count)).where(
            and_(Property.deleted_at.is_(None), Property.updated_at >= today_start)
        )
        total_views_today = (await db.execute(total_views_today_query)).scalar_one() or 0
        
        total_views_week_query = select(func.sum(Property.view_count)).where(
            and_(Property.deleted_at.is_(None), Property.updated_at >= week_start)
        )
        total_views_this_week = (await db.execute(total_views_week_query)).scalar_one() or 0
        
        total_searches_today_query = select(func.count(SearchQuery.id)).where(
            SearchQuery.created_at >= today_start
        )
        total_searches_today = (await db.execute(total_searches_today_query)).scalar_one()
        
        total_searches_week_query = select(func.count(SearchQuery.id)).where(
            SearchQuery.created_at >= week_start
        )
        total_searches_this_week = (await db.execute(total_searches_week_query)).scalar_one()
        
        return PlatformStatistics(
            total_users=total_users,
            active_users=active_users,
            verified_users=verified_users,
            new_users_today=new_users_today,
            new_users_this_week=new_users_this_week,
            new_users_this_month=new_users_this_month,
            total_properties=total_properties,
            active_listings=active_listings,
            draft_listings=draft_listings,
            sold_listings=sold_listings,
            expired_listings=expired_listings,
            new_properties_today=new_properties_today,
            new_properties_this_week=new_properties_this_week,
            new_properties_this_month=new_properties_this_month,
            total_views_today=int(total_views_today),
            total_views_this_week=int(total_views_this_week),
            total_searches_today=total_searches_today,
            total_searches_this_week=total_searches_this_week
        )
    
    @staticmethod
    async def get_user_growth(db: AsyncSession, days: int = 30) -> List[UserGrowthData]:
        """Get user growth data over time"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query daily user registrations
        query = select(
            func.date_trunc('day', User.created_at).label('date'),
            func.count(User.id).label('new_users')
        ).where(
            and_(
                User.deleted_at.is_(None),
                User.created_at >= start_date
            )
        ).group_by(
            func.date_trunc('day', User.created_at)
        ).order_by('date')
        
        result = await db.execute(query)
        daily_data = result.all()
        
        # Calculate cumulative totals
        growth_data = []
        cumulative_total = 0
        
        for row in daily_data:
            cumulative_total += row.new_users
            growth_data.append(UserGrowthData(
                date=row.date,
                new_users=row.new_users,
                total_users=cumulative_total,
                active_users=cumulative_total  # Simplified - would need separate active user tracking
            ))
        
        return growth_data
    
    @staticmethod
    async def get_property_growth(db: AsyncSession, days: int = 30) -> List[PropertyGrowthData]:
        """Get property growth data over time"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query daily property creation
        query = select(
            func.date_trunc('day', Property.created_at).label('date'),
            func.count(Property.id).label('new_properties')
        ).where(
            and_(
                Property.deleted_at.is_(None),
                Property.created_at >= start_date
            )
        ).group_by(
            func.date_trunc('day', Property.created_at)
        ).order_by('date')
        
        result = await db.execute(query)
        daily_data = result.all()
        
        # Calculate cumulative totals
        growth_data = []
        cumulative_total = 0
        
        for row in daily_data:
            cumulative_total += row.new_properties
            growth_data.append(PropertyGrowthData(
                date=row.date,
                new_properties=row.new_properties,
                total_properties=cumulative_total,
                active_properties=cumulative_total  # Simplified
            ))
        
        return growth_data
    
    @staticmethod
    async def get_city_statistics(db: AsyncSession, limit: int = 10) -> List[CityStatistics]:
        """Get property statistics by city"""
        query = select(
            Property.city,
            func.count(Property.id).label('property_count'),
            func.sum(case((Property.status == PropertyStatus.ACTIVE, 1), else_=0)).label('active_count'),
            func.avg(Property.price).label('avg_price'),
            func.sum(Property.view_count).label('total_views')
        ).where(
            Property.deleted_at.is_(None)
        ).group_by(
            Property.city
        ).order_by(
            desc('property_count')
        ).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            CityStatistics(
                city=row.city,
                property_count=row.property_count,
                active_count=row.active_count or 0,
                avg_price=float(row.avg_price or 0),
                total_views=row.total_views or 0
            )
            for row in rows
        ]
    
    @staticmethod
    async def get_user_role_distribution(db: AsyncSession) -> List[UserRoleDistribution]:
        """Get distribution of users by role"""
        total_users_query = select(func.count(User.id)).where(User.deleted_at.is_(None))
        total_users = (await db.execute(total_users_query)).scalar_one()
        
        if total_users == 0:
            return []
        
        query = select(
            User.role,
            func.count(User.id).label('count')
        ).where(
            User.deleted_at.is_(None)
        ).group_by(
            User.role
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            UserRoleDistribution(
                role=row.role,
                count=row.count,
                percentage=round((row.count / total_users) * 100, 2)
            )
            for row in rows
        ]
    
    @staticmethod
    async def get_property_type_distribution(db: AsyncSession) -> List[PropertyTypeDistribution]:
        """Get distribution of properties by type"""
        total_properties_query = select(func.count(Property.id)).where(Property.deleted_at.is_(None))
        total_properties = (await db.execute(total_properties_query)).scalar_one()
        
        if total_properties == 0:
            return []
        
        query = select(
            Property.property_type,
            func.count(Property.id).label('count')
        ).where(
            Property.deleted_at.is_(None)
        ).group_by(
            Property.property_type
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            PropertyTypeDistribution(
                property_type=row.property_type,
                count=row.count,
                percentage=round((row.count / total_properties) * 100, 2)
            )
            for row in rows
        ]
    
    @staticmethod
    async def get_recent_activity(db: AsyncSession, limit: int = 20) -> List[RecentActivity]:
        """Get recent platform activity"""
        activities = []
        
        # Recent user registrations
        recent_users_query = select(User).where(
            User.deleted_at.is_(None)
        ).order_by(
            User.created_at.desc()
        ).limit(limit // 2)
        
        recent_users = (await db.execute(recent_users_query)).scalars().all()
        
        for user in recent_users:
            activities.append(RecentActivity(
                activity_type="user_registration",
                description=f"New {user.role.value} registered: {user.email}",
                user_id=user.id,
                user_email=user.email,
                timestamp=user.created_at
            ))
        
        # Recent property listings
        recent_properties_query = select(Property, User).join(
            User, Property.owner_id == User.id
        ).where(
            Property.deleted_at.is_(None)
        ).order_by(
            Property.created_at.desc()
        ).limit(limit // 2)
        
        result = await db.execute(recent_properties_query)
        recent_properties = result.all()
        
        for prop, owner in recent_properties:
            activities.append(RecentActivity(
                activity_type="property_created",
                description=f"New property listed: {prop.title}",
                user_id=owner.id,
                user_email=owner.email,
                entity_id=prop.id,
                timestamp=prop.created_at
            ))
        
        # Sort by timestamp
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        
        return activities[:limit]
    
    @staticmethod
    async def search_users(
        db: AsyncSession,
        email: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_desc"
    ) -> Tuple[List[User], int]:
        """Search users with filters"""
        
        # Build query
        query = select(User).where(User.deleted_at.is_(None))
        
        # Apply filters
        if email:
            query = query.where(User.email.ilike(f"%{email}%"))
        
        if role:
            query = query.where(User.role == role)
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        if is_verified is not None:
            query = query.where(User.is_verified == is_verified)
        
        if created_after:
            query = query.where(User.created_at >= created_after)
        
        if created_before:
            query = query.where(User.created_at <= created_before)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()
        
        # Apply sorting
        if sort_by == "created_desc":
            query = query.order_by(User.created_at.desc())
        elif sort_by == "created_asc":
            query = query.order_by(User.created_at.asc())
        elif sort_by == "email":
            query = query.order_by(User.email)
        elif sort_by == "last_login":
            query = query.order_by(User.last_login.desc().nullslast())
        
        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute
        result = await db.execute(query)
        users = list(result.scalars().all())
        
        return users, total
    
    @staticmethod
    async def moderate_user(
        db: AsyncSession,
        user_id: UUID,
        action: str,
        admin_id: UUID,
        reason: Optional[str] = None
    ) -> User:
        """Moderate user account"""
        
        # Get user
        user_query = select(User).where(User.id == user_id)
        user = (await db.execute(user_query)).scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Apply action
        if action == "activate":
            user.is_active = True
        elif action == "deactivate":
            user.is_active = False
        elif action == "verify":
            user.is_verified = True
        elif action == "ban":
            user.is_active = False
            user.deleted_at = datetime.utcnow()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}"
            )
        
        await db.flush()
        await db.refresh(user)
        
        # TODO: Create audit log entry
        
        return user
    
    @staticmethod
    async def moderate_property(
        db: AsyncSession,
        property_id: UUID,
        action: str,
        admin_id: UUID,
        reason: Optional[str] = None
    ) -> Property:
        """Moderate property listing"""
        
        # Get property
        property_query = select(Property).where(Property.id == property_id)
        property_obj = (await db.execute(property_query)).scalar_one_or_none()
        
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        # Apply action
        if action == "approve":
            property_obj.status = PropertyStatus.ACTIVE
            if not property_obj.published_at:
                property_obj.published_at = datetime.utcnow()
                property_obj.expires_at = datetime.utcnow() + timedelta(days=60)
        elif action == "reject":
            property_obj.status = PropertyStatus.DRAFT
        elif action == "flag":
            # Mark as requiring review (would need additional field)
            pass
        elif action == "remove":
            property_obj.status = PropertyStatus.EXPIRED
            property_obj.deleted_at = datetime.utcnow()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}"
            )
        
        await db.flush()
        await db.refresh(property_obj)
        
        # TODO: Create audit log entry
        # TODO: Notify owner if notify_owner is True
        
        return property_obj


admin_service = AdminService()
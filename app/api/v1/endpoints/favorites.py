from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from math import ceil

from app.core.database import get_db
from app.models.user import User
from app.schemas.favorite import (
    FavoriteCreate,
    FavoriteUpdate,
    FavoriteResponse,
    FavoriteStats
)
from app.services.favorite_service import favorite_service
from app.api.dependencies import get_current_user

router = APIRouter()


@router.post("", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
async def add_to_favorites(
    favorite_data: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add property to favorites
    
    **Features:**
    - Validates property exists
    - Prevents duplicates
    - Increments favorite_count on property
    - Optional notes
    """
    favorite = await favorite_service.add_favorite(
        db,
        current_user.id,
        favorite_data
    )
    return favorite


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_favorites(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove property from favorites
    
    **Features:**
    - Decrements favorite_count on property
    """
    success = await favorite_service.remove_favorite(
        db,
        current_user.id,
        property_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )


@router.patch("/{property_id}", response_model=FavoriteResponse)
async def update_favorite_notes(
    property_id: UUID,
    update_data: FavoriteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update favorite notes
    """
    favorite = await favorite_service.update_favorite(
        db,
        current_user.id,
        property_id,
        update_data
    )
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )
    
    return favorite


@router.get("", response_model=dict)
async def get_my_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's favorite properties with pagination
    
    **Returns:**
    - Paginated list of favorites with property details
    - Total count
    """
    skip = (page - 1) * page_size
    
    favorites, total = await favorite_service.get_user_favorites(
        db,
        current_user.id,
        skip,
        page_size
    )
    
    # Load property details for each favorite
    from app.services.property_service import property_service
    
    favorites_with_properties = []
    for fav in favorites:
        prop = await property_service.get_by_id(db, fav.property_id)
        if prop:
            favorites_with_properties.append({
                "id": fav.id,
                "property_id": fav.property_id,
                "notes": fav.notes,
                "created_at": fav.created_at,
                "property": {
                    "id": prop.id,
                    "title": prop.title,
                    "price": float(prop.price),
                    "property_type": prop.property_type,
                    "listing_type": prop.listing_type,
                    "city": prop.city,
                    "neighborhood": prop.neighborhood,
                    "main_photo": prop.main_photo,
                    "slug": prop.slug,
                    "rooms": prop.rooms,
                    "total_area": float(prop.total_area)
                }
            })
    
    total_pages = ceil(total / page_size) if total > 0 else 0
    
    return {
        "items": favorites_with_properties,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/check/{property_id}", response_model=dict)
async def check_if_favorited(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if property is in user's favorites
    """
    is_favorited = await favorite_service.is_favorited(
        db,
        current_user.id,
        property_id
    )
    
    return {"is_favorited": is_favorited}


@router.get("/stats", response_model=FavoriteStats)
async def get_favorites_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics about user's favorites
    
    **Returns:**
    - Total count
    - For sale vs for rent breakdown
    - Average price
    - Top cities
    """
    stats = await favorite_service.get_favorites_stats(
        db,
        current_user.id
    )
    
    return stats

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.schemas.alerts import (
    SavedSearchCreate,
    SavedSearchUpdate,
    SavedSearchResponse,
    FavoriteCreate,
    FavoriteResponse,
    FavoriteWithProperty
)
from app.schemas.user import Message
from app.services.alert_service import alert_service
from app.api.dependencies import get_current_user

router = APIRouter()


# ============ SAVED SEARCHES ============

@router.post("/saved-searches", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    search_data: SavedSearchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new saved search with alert preferences
    
    **Features:**
    - Save complex search queries
    - Configure alert frequency (instant, daily, weekly)
    - Enable/disable alerts for new listings
    - Enable/disable alerts for price drops
    
    **Example:**
    ```json
    {
      "name": "3-Room Apartments in Bucharest",
      "search_params": {
        "city": "Bucharest",
        "property_type": "apartment",
        "min_rooms": 3,
        "max_rooms": 3,
        "max_price": 150000
      },
      "alert_enabled": true,
      "alert_frequency": "instant",
      "alert_new_listings": true,
      "alert_price_drops": true
    }
    ```
    """
    saved_search = await alert_service.create_saved_search(
        db, current_user.id, search_data
    )
    
    # Get current matching count
    matching_count = await alert_service.get_matching_count(db, saved_search.search_params)
    
    response = SavedSearchResponse.model_validate(saved_search)
    response.matching_count = matching_count
    
    return response


@router.get("/saved-searches", response_model=List[SavedSearchResponse])
async def get_saved_searches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all saved searches for current user
    
    Returns list of saved searches with current matching counts
    """
    saved_searches = await alert_service.get_user_saved_searches(db, current_user.id)
    
    # Add matching counts
    response = []
    for search in saved_searches:
        search_response = SavedSearchResponse.model_validate(search)
        search_response.matching_count = await alert_service.get_matching_count(
            db, search.search_params
        )
        response.append(search_response)
    
    return response


@router.get("/saved-searches/{search_id}", response_model=SavedSearchResponse)
async def get_saved_search(
    search_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific saved search by ID"""
    saved_search = await alert_service.get_saved_search_by_id(
        db, search_id, current_user.id
    )
    
    if not saved_search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )
    
    response = SavedSearchResponse.model_validate(saved_search)
    response.matching_count = await alert_service.get_matching_count(
        db, saved_search.search_params
    )
    
    return response


@router.put("/saved-searches/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: UUID,
    search_data: SavedSearchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a saved search
    
    Can update:
    - Name
    - Search parameters
    - Alert settings (enabled, frequency, types)
    """
    saved_search = await alert_service.update_saved_search(
        db, search_id, current_user.id, search_data
    )
    
    if not saved_search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )
    
    response = SavedSearchResponse.model_validate(saved_search)
    response.matching_count = await alert_service.get_matching_count(
        db, saved_search.search_params
    )
    
    return response


@router.delete("/saved-searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a saved search"""
    success = await alert_service.delete_saved_search(db, search_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )


# ============ FAVORITES ============

@router.post("/favorites", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    favorite_data: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a property to favorites
    
    **Features:**
    - Save properties for later viewing
    - Add optional notes
    - Get price drop alerts automatically
    
    **Example:**
    ```json
    {
      "property_id": "123e4567-e89b-12d3-a456-426614174000",
      "notes": "Great location, need to schedule viewing"
    }
    ```
    """
    favorite = await alert_service.add_favorite(db, current_user.id, favorite_data)
    return favorite


@router.get("/favorites", response_model=List[FavoriteWithProperty])
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all favorited properties
    
    Returns favorites with full property details
    """
    favorites = await alert_service.get_user_favorites(
        db, current_user.id, include_property_details=True
    )
    
    # Format response with property details
    response = []
    for favorite in favorites:
        fav_dict = {
            'id': favorite.id,
            'user_id': favorite.user_id,
            'property_id': favorite.property_id,
            'notes': favorite.notes,
            'created_at': favorite.created_at,
            'property': {
                'id': str(favorite.property.id),
                'title': favorite.property.title,
                'price': float(favorite.property.price),
                'city': favorite.property.city,
                'property_type': favorite.property.property_type,
                'listing_type': favorite.property.listing_type,
                'rooms': favorite.property.rooms,
                'total_area': float(favorite.property.total_area),
                'main_photo': favorite.property.main_photo,
                'slug': favorite.property.slug,
                'status': favorite.property.status
            }
        }
        response.append(FavoriteWithProperty(**fav_dict))
    
    return response


@router.delete("/favorites/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a property from favorites"""
    success = await alert_service.remove_favorite(db, current_user.id, property_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )


@router.get("/favorites/check/{property_id}")
async def check_favorite(
    property_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a property is favorited
    
    Useful for UI to show favorite status
    """
    from sqlalchemy import select, and_
    from app.models.alerts import Favorite
    
    result = await db.execute(
        select(Favorite.id).where(
            and_(
                Favorite.user_id == current_user.id,
                Favorite.property_id == property_id
            )
        )
    )
    
    is_favorited = result.scalar_one_or_none() is not None
    
    return {"is_favorited": is_favorited}
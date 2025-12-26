from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.schemas.saved_search import (
    SavedSearchCreate,
    SavedSearchUpdate,
    SavedSearchResponse
)
from app.services.saved_search_service import saved_search_service
from app.api.dependencies import get_current_user

router = APIRouter()


@router.post("", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    search_data: SavedSearchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Save a search query for future use and notifications
    
    **Features:**
    - Save any search filter combination
    - Custom name and description
    - Email notification settings
    - Maximum 20 saved searches per user
    """
    saved_search = await saved_search_service.create_saved_search(
        db,
        current_user.id,
        search_data
    )
    return saved_search


@router.get("", response_model=List[SavedSearchResponse])
async def get_my_saved_searches(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all user's saved searches
    
    **Query Parameters:**
    - active_only: Filter to only active searches (default: true)
    """
    saved_searches = await saved_search_service.get_user_saved_searches(
        db,
        current_user.id,
        active_only
    )
    return saved_searches


@router.get("/{search_id}", response_model=SavedSearchResponse)
async def get_saved_search(
    search_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific saved search by ID
    """
    saved_search = await saved_search_service.get_saved_search(
        db,
        search_id,
        current_user.id
    )
    
    if not saved_search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )
    
    return saved_search


@router.put("/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: UUID,
    update_data: SavedSearchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update saved search
    
    **Updatable fields:**
    - name
    - description
    - filters
    - email_notifications
    - notification_frequency
    - is_active
    """
    saved_search = await saved_search_service.update_saved_search(
        db,
        search_id,
        current_user.id,
        update_data
    )
    
    if not saved_search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )
    
    return saved_search


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete saved search
    """
    success = await saved_search_service.delete_saved_search(
        db,
        search_id,
        current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )


@router.post("/{search_id}/execute", response_model=dict)
async def execute_saved_search(
    search_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a saved search and return current results
    
    **Features:**
    - Runs the saved search query
    - Updates last_checked_at timestamp
    - Updates result_count
    - Returns properties matching the search
    """
    saved_search = await saved_search_service.get_saved_search(
        db,
        search_id,
        current_user.id
    )
    
    if not saved_search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found"
        )
    
    properties, total = await saved_search_service.execute_saved_search(
        db,
        saved_search
    )
    
    from app.schemas.property import PropertyListItem
    
    return {
        "saved_search": SavedSearchResponse.model_validate(saved_search),
        "results": {
            "items": [PropertyListItem.model_validate(p) for p in properties[:20]],
            "total": total
        }
    }

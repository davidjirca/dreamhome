from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from math import ceil

from app.core.database import get_db
from app.models.user import User
from app.schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyListItem,
    PropertySearchParams,
    PropertySearchResponse
)
from app.services.property_service import property_service
from app.api.dependencies import get_current_user, require_agent_or_owner
from app.models.property import PropertyType, ListingType

router = APIRouter()


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
        property_data: PropertyCreate,
        current_user: User = Depends(require_agent_or_owner),
        db: AsyncSession = Depends(get_db)
):
    """
    Create new property listing

    Requires: Owner, Agent, or Admin role
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
    """Get property by ID"""
    property_obj = await property_service.get_by_id(db, property_id)

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )

    return property_obj


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
        property_id: UUID,
        property_data: PropertyUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Update property listing"""
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
    """Soft delete property"""
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
    """Publish property listing"""
    property_obj = await property_service.publish_property(
        db,
        property_id,
        current_user.id
    )
    return property_obj


@router.get("", response_model=PropertySearchResponse)
async def search_properties(
        city: Optional[str] = None,
        property_type: Optional[PropertyType] = None,
        listing_type: Optional[ListingType] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rooms: Optional[int] = None,
        max_rooms: Optional[int] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        sort_by: str = Query(default="newest"),
        db: AsyncSession = Depends(get_db)
):
    """
    Search properties with filters

    Sort options: newest, price_asc, price_desc, area_desc
    """
    # Create search params
    params = PropertySearchParams(
        city=city,
        property_type=property_type,
        listing_type=listing_type,
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        min_area=min_area,
        max_area=max_area,
        page=page,
        page_size=page_size,
        sort_by=sort_by
    )

    # Execute search
    properties, total = await property_service.search_properties(db, params)

    # Calculate total pages
    total_pages = ceil(total / page_size)

    return PropertySearchResponse(
        items=properties,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
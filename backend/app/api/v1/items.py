from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.crud.item import (
    get_item_by_id,
    get_item_by_name,
    get_items,
    create_item,
    update_item,
    update_item_status,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.item import ItemCreate, ItemUpdate, ItemStatusUpdate, ItemOut
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/items", tags=["1. Masters - Items"])


@router.post(
    "",
    response_model=SuccessResponse[ItemOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Item",
    description="Create a new item master record with auto-generated code and GST details."
)
def create_new_item(
    item_in: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = create_item(db, item_in)
    return SuccessResponse(
        success=True,
        message="Item created successfully",
        data=ItemOut.model_validate(item),
    )


@router.get(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="List Items",
    description="Retrieve items with optional category filter, search term, status filter ('active', 'inactive', 'all'), and pagination."
)
def list_items(
    search: Optional[str] = Query(None, description="Search by item name, code, description, or HSN"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    status: Optional[str] = Query("all", description="Filter by status: 'active', 'inactive', or 'all'"),
    skip: int = Query(0, ge=0, description="Records to skip for pagination"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_items(db, skip=skip, limit=limit, search=search, category=category, status=status)
    return SuccessResponse(
        success=True,
        message="Items retrieved successfully",
        data={
            "items": [ItemOut.model_validate(i) for i in items],
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    )


@router.get(
    "/{item_name}",
    response_model=SuccessResponse[ItemOut],
    summary="Get Item Details",
    description="Retrieve a single item master by its name, code, or numeric ID."
)
def get_item(
    item_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_item_by_name(db, item_name)
    if not item and item_name.isdigit():
        item = get_item_by_id(db, int(item_name))
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_name}' not found.",
        )
    return SuccessResponse(
        success=True,
        message="Item details retrieved successfully",
        data=ItemOut.model_validate(item),
    )


@router.put(
    "/{item_name}",
    response_model=SuccessResponse[ItemOut],
    summary="Update Item",
    description="Update fields of an existing item master record by name, code, or numeric ID."
)
def update_existing_item(
    item_name: str,
    item_in: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_item_by_name(db, item_name)
    if not item and item_name.isdigit():
        item = get_item_by_id(db, int(item_name))
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_name}' not found.",
        )

    updated = update_item(db, item, item_in)
    return SuccessResponse(
        success=True,
        message="Item updated successfully",
        data=ItemOut.model_validate(updated),
    )


@router.patch(
    "/{item_name}/status",
    response_model=SuccessResponse[ItemOut],
    summary="Toggle Item Status (Soft Delete)",
    description="Activate or deactivate an item master by name, code, or numeric ID."
)
def change_item_status(
    item_name: str,
    status_in: ItemStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_item_by_name(db, item_name)
    if not item and item_name.isdigit():
        item = get_item_by_id(db, int(item_name))
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_name}' not found.",
        )

    updated = update_item_status(db, item, status_in.status)
    status_label = "activated" if status_in.status else "deactivated"
    return SuccessResponse(
        success=True,
        message=f"Item has been {status_label} successfully",
        data=ItemOut.model_validate(updated),
    )


@router.patch(
    "/{item_name}/toggle-status",
    response_model=SuccessResponse[ItemOut],
    summary="Toggle Item Status",
    description="Toggle active/inactive status of an item."
)
def toggle_item_status(
    item_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_item_by_name(db, item_name)
    if not item and item_name.isdigit():
        item = get_item_by_id(db, int(item_name))
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_name}' not found.",
        )

    updated = update_item_status(db, item, not item.status)
    status_label = "activated" if updated.status else "deactivated"
    return SuccessResponse(
        success=True,
        message=f"Item has been {status_label} successfully",
        data=ItemOut.model_validate(updated),
    )

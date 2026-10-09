"""
Outward & Dispatch Management API Endpoints
Handles Delivery Challans, stock deduction, draft updates, and order dispatch workflows.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.outward import OutwardCreate, OutwardUpdate, OutwardOut, OutwardListOut
from app.schemas.response import SuccessResponse
from app.crud.outward import (
    create_outward, update_outward, post_outward,
    get_outward_by_id, get_outwards, format_outward_out
)

router = APIRouter(prefix="/sales/outward", tags=["2. Sales - Outward (Dispatch)"])
api_alias_router = APIRouter(prefix="/api/outward", tags=["2. Sales - Outward (Dispatch)"])


@router.post(
    "",
    response_model=SuccessResponse[OutwardOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Delivery Challan (Outward Dispatch)",
    description=(
        "Create a Delivery Challan for a Customer Order. "
        "Validates available stock in inventory and order pending quantity, "
        "deducts stock with Stock Ledger OUT entries, updates Stock Summary, "
        "and updates Customer Order and Customer Request status upon full fulfillment."
    ),
)
@api_alias_router.post(
    "",
    response_model=SuccessResponse[OutwardOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Delivery Challan (Outward Dispatch)",
)
def create_delivery_challan(
    outward_in: OutwardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        outward = create_outward(db=db, obj_in=outward_in, user_id=current_user.id)
        return SuccessResponse(
            success=True,
            message="Delivery Challan created successfully.",
            data=format_outward_out(outward),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.put(
    "/{id}",
    response_model=SuccessResponse[OutwardOut],
    summary="Update Draft Outward Document",
    description="Update a Delivery Challan in Draft status. Posted documents are immutable.",
)
@api_alias_router.put(
    "/{id}",
    response_model=SuccessResponse[OutwardOut],
    summary="Update Draft Outward Document",
)
def edit_outward(
    id: int,
    outward_in: OutwardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        outward = update_outward(db=db, outward_id=id, obj_in=outward_in)
        return SuccessResponse(
            success=True,
            message="Delivery Challan updated successfully.",
            data=format_outward_out(outward),
        )
    except ValueError as exc:
        msg = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=msg)


@router.post(
    "/{id}/post",
    response_model=SuccessResponse[OutwardOut],
    summary="Post Delivery Challan",
    description="Post a Draft Delivery Challan, validate on-hand inventory, and execute stock OUT movement.",
)
@api_alias_router.post(
    "/{id}/post",
    response_model=SuccessResponse[OutwardOut],
    summary="Post Delivery Challan",
)
def post_delivery_challan(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        outward = post_outward(db=db, outward_id=id, user_id=current_user.id)
        return SuccessResponse(
            success=True,
            message="Delivery Challan posted successfully and stock deducted from inventory.",
            data=format_outward_out(outward),
        )
    except ValueError as exc:
        msg = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=msg)


@router.get(
    "",
    response_model=SuccessResponse[OutwardListOut],
    summary="List Outward Documents",
    description="Retrieve list of Outward documents / Delivery Challans with pagination and filters.",
)
@api_alias_router.get(
    "",
    response_model=SuccessResponse[OutwardListOut],
    summary="List Outward Documents",
)
def list_outwards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status (Draft, Dispatched, Partially Dispatched, Invoiced)"),
    customer_request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    customer_order_id: Optional[int] = Query(None, description="Filter by Customer Order ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_outwards(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        customer_request_id=customer_request_id,
        customer_order_id=customer_order_id,
    )
    data = OutwardListOut(
        total=total,
        items=[format_outward_out(outw) for outw in items],
    )
    return SuccessResponse(
        success=True,
        message="Outward documents retrieved successfully.",
        data=data,
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[OutwardOut],
    summary="Get Outward Document Details",
    description="Retrieve details of a single Outward document by its ID.",
)
@api_alias_router.get(
    "/{id}",
    response_model=SuccessResponse[OutwardOut],
    summary="Get Outward Document Details",
)
def get_outward(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    outward = get_outward_by_id(db, id)
    if not outward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outward document with ID {id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Outward document retrieved successfully.",
        data=format_outward_out(outward),
    )

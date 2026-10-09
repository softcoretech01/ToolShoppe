from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.grn import GRNCreate, GRNOut, GRNListOut
from app.schemas.response import SuccessResponse
from app.crud.grn import (
    create_grn, get_grn_by_id, get_grns, format_grn_out
)

router = APIRouter(prefix="/purchase/grn", tags=["3. Purchase - Goods Receipt Note (GRN)"])


@router.post(
    "",
    response_model=SuccessResponse[GRNOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Goods Receipt Note (GRN)",
    description=(
        "Receive goods against a sent Purchase Order. Validates received quantity against "
        "outstanding order balance, verifies accepted + rejected quantities, updates PO status, "
        "and automatically generates an Inward document containing accepted quantities."
    ),
)
def create_goods_receipt(
    obj_in: GRNCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        grn = create_grn(db=db, obj_in=obj_in)
        return SuccessResponse(
            success=True,
            message="Goods Receipt Note created successfully.",
            data=format_grn_out(grn),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=SuccessResponse[GRNListOut],
    summary="List Goods Receipt Notes",
    description="Retrieve list of GRNs with pagination and optional filtering.",
)
def list_goods_receipts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status (Received)"),
    purchase_order_id: Optional[int] = Query(None, description="Filter by Purchase Order ID"),
    customer_request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_grns(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        purchase_order_id=purchase_order_id,
        customer_request_id=customer_request_id,
    )
    data = GRNListOut(
        total=total,
        items=[format_grn_out(g) for g in items],
    )
    return SuccessResponse(
        success=True,
        message="Goods receipt notes retrieved successfully.",
        data=data,
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[GRNOut],
    summary="Get Goods Receipt Note Details",
    description="Retrieve details of a single Goods Receipt Note by its ID.",
)
def get_goods_receipt(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    grn = get_grn_by_id(db, id)
    if not grn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goods Receipt Note with ID {id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Goods receipt note retrieved successfully.",
        data=format_grn_out(grn),
    )

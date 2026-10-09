from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.inward import InwardOut, InwardListOut
from app.schemas.response import SuccessResponse
from app.crud.inward import (
    get_inward_by_id, get_inwards, add_inward_to_inventory, format_inward_out
)

router = APIRouter(prefix="/purchase/inward", tags=["3. Purchase - Inward"])


@router.get(
    "",
    response_model=SuccessResponse[InwardListOut],
    summary="List Inward Documents",
    description="Retrieve list of Inward documents with pagination and optional filtering.",
)
def list_inwards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status (Pending, Added)"),
    customer_request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_inwards(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        customer_request_id=customer_request_id,
    )
    data = InwardListOut(
        total=total,
        items=[format_inward_out(inw) for inw in items],
    )
    return SuccessResponse(
        success=True,
        message="Inward documents retrieved successfully.",
        data=data,
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[InwardOut],
    summary="Get Inward Document Details",
    description="Retrieve details of a single Inward document by its ID.",
)
def get_inward(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inward = get_inward_by_id(db, id)
    if not inward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inward document with ID {id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Inward document retrieved successfully.",
        data=format_inward_out(inward),
    )


@router.post(
    "/{id}/add",
    response_model=SuccessResponse[InwardOut],
    summary="Add Inward to Inventory",
    description=(
        "Post accepted stock quantities to inventory: creates stock ledger entries, "
        "updates stock summary for the customer request, updates item last purchase rates, "
        "marks inward as 'Added', and transitions customer request to 'Stock In'."
    ),
)
def add_to_inventory(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        inward = add_inward_to_inventory(db=db, inward_id=id)
        return SuccessResponse(
            success=True,
            message="Stock successfully added to inventory.",
            data=format_inward_out(inward),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

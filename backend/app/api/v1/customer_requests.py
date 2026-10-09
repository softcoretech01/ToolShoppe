from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.customer import Customer
from app.crud.customer import get_customer_by_name
from app.crud.item import get_item_by_name, get_item_by_id
from app.schemas.customer_request import (
    CustomerRequestCreate, CustomerRequestUpdate, CustomerRequestOut
)
from app.schemas.response import SuccessResponse
from app.crud.customer_request import (
    get_customer_request_by_id,
    get_customer_requests,
    create_customer_request,
    update_customer_request,
    format_cr_out,
)

router = APIRouter(prefix="/sales/customer-request", tags=["2. Sales - Customer Request"])


@router.post(
    "",
    response_model=SuccessResponse[CustomerRequestOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Customer Request",
    description=(
        "Create a new Customer Request with multiple item lines. "
        "Automatically generates CR number and a matching Purchase Request (PR) with identical lines."
    )
)
def create_new_cr(
    cr_in: CustomerRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = None
    if cr_in.customer_id is not None:
        customer = db.query(Customer).filter(Customer.id == cr_in.customer_id).first()
    if not customer and cr_in.customer_name:
        customer = get_customer_by_name(db, cr_in.customer_name)
    if not customer:
        ident = cr_in.customer_name or cr_in.customer_id
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{ident}' does not exist.",
        )
    cr_in.customer_id = customer.id

    for line in cr_in.lines:
        if line.item_id is None and line.item_name:
            item = get_item_by_name(db, line.item_name)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item '{line.item_name}' does not exist.",
                )
            line.item_id = item.id
            if not line.unit and item.unit:
                line.unit = item.unit
        elif line.item_id is not None:
            item = get_item_by_id(db, line.item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item with ID {line.item_id} does not exist.",
                )
            if not line.unit and item.unit:
                line.unit = item.unit
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each line must provide either item_name or item_id.",
            )

    cr = create_customer_request(db, cr_in, user_id=current_user.id)
    return SuccessResponse(
        success=True,
        message="Customer request created successfully; Purchase Request generated automatically.",
        data=format_cr_out(cr),
    )


@router.get(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="List Customer Requests",
    description="Retrieve Customer Requests with optional search, status filtering, and pagination."
)
def list_crs(
    search: Optional[str] = Query(None, description="Search by request number, customer name, code, or reference"),
    status: Optional[str] = Query("all", description="Filter by status (e.g. 'Requested', 'RFQ Sent', 'Quoted', 'Approved', or 'all')"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_customer_requests(db, skip=skip, limit=limit, search=search, status=status)
    return SuccessResponse(
        success=True,
        message="Customer requests retrieved successfully",
        data={
            "items": [format_cr_out(cr) for cr in items],
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    )


@router.get(
    "/{cr_id}",
    response_model=SuccessResponse[CustomerRequestOut],
    summary="Get Customer Request Details",
    description="Retrieve full details and line items of a single Customer Request."
)
def get_cr(
    cr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cr = get_customer_request_by_id(db, cr_id)
    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer Request with ID {cr_id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Customer request retrieved successfully",
        data=format_cr_out(cr),
    )


@router.put(
    "/{cr_id}",
    response_model=SuccessResponse[CustomerRequestOut],
    summary="Update Customer Request",
    description="Edit a Customer Request. Allowed only while status is 'Requested' (prior to RFQ dispatch)."
)
def update_cr(
    cr_id: int,
    cr_in: CustomerRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cr = get_customer_request_by_id(db, cr_id)
    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer Request with ID {cr_id} not found.",
        )

    if cr_in.customer_name and cr_in.customer_id is None:
        customer = get_customer_by_name(db, cr_in.customer_name)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer '{cr_in.customer_name}' does not exist.",
            )
        cr_in.customer_id = customer.id

    if cr_in.lines:
        for line in cr_in.lines:
            if line.item_id is None and line.item_name:
                item = get_item_by_name(db, line.item_name)
                if not item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Item '{line.item_name}' does not exist.",
                    )
                line.item_id = item.id
                if not line.unit and item.unit:
                    line.unit = item.unit

    try:
        updated = update_customer_request(db, cr, cr_in)
        return SuccessResponse(
            success=True,
            message="Customer request updated successfully",
            data=format_cr_out(updated),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

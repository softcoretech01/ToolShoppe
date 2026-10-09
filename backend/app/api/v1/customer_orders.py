from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.customer_order import (
    CustomerOrderCreate, CustomerOrderOut, CustomerOrderListOut
)
from app.schemas.response import SuccessResponse
from app.crud.customer_order import (
    create_customer_order, get_customer_order_by_id, get_customer_orders, format_co_out
)

router = APIRouter(prefix="/sales/customer-order", tags=["2. Sales - Customer Order"])


@router.post(
    "",
    response_model=SuccessResponse[CustomerOrderOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Customer Purchase Order (Sales Order)",
    description=(
        "Create Customer PO from an accepted Customer Quotation. "
        "Automatically generates Supplier Purchase Order using the original supplier quotation rates. "
        "Updates Customer Request stage to 'PO Created'."
    )
)
def create_order(
    order_in: CustomerOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        co = create_customer_order(db, order_in)
        return SuccessResponse(
            success=True,
            message="Customer PO saved successfully. Supplier Purchase Order created automatically.",
            data=format_co_out(co),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=SuccessResponse[CustomerOrderListOut],
    summary="List Customer Orders",
    description="Retrieve list of customer orders with pagination and optional status filter."
)
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status (Open, etc.)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_customer_orders(db=db, skip=skip, limit=limit, status=status)
    data = CustomerOrderListOut(
        total=total,
        items=[format_co_out(co) for co in items],
    )
    return SuccessResponse(
        success=True,
        message="Customer orders retrieved successfully.",
        data=data,
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[CustomerOrderOut],
    summary="Get Customer Order Details",
    description="Retrieve details of a single Customer Order by its ID."
)
def get_order(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    co = get_customer_order_by_id(db, id)
    if not co:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer Order with ID {id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Customer order retrieved successfully.",
        data=format_co_out(co),
    )

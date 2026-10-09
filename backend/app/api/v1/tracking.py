from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.tracking import OrderTrackingOut
from app.schemas.response import SuccessResponse
from app.crud.tracking import get_order_tracking

router = APIRouter(tags=["5. Order Tracking & Audit"])


@router.get(
    "/track/{customer_request_id}",
    response_model=SuccessResponse[OrderTrackingOut],
    summary="Get Sourcing Order Tracking Timeline",
    description=(
        "Retrieve the complete sourcing timeline and linked documents for a Customer Request. "
        "Aggregates Customer Request, Purchase Request, RFQ dispatches, Vendor Quotations, "
        "Comparison, Orders, Inward, Outward, Invoicing, and Margin into a chronological audit trail."
    )
)
@router.get(
    "/tracking/{customer_request_id}",
    response_model=SuccessResponse[OrderTrackingOut],
    summary="Get Order Tracking (Tracking prefix)",
)
@router.get(
    "/api/tracking/{customer_request_id}",
    response_model=SuccessResponse[OrderTrackingOut],
    summary="Get Order Tracking (API prefix)",
)
def track_customer_request(
    customer_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        tracking = get_order_tracking(db, customer_request_id)
        return SuccessResponse(
            success=True,
            message="Order tracking timeline retrieved successfully.",
            data=tracking,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/customer-request/{customer_request_id}/track",
    response_model=SuccessResponse[OrderTrackingOut],
    summary="Get Order Tracking (Alias)",
    description="Alias endpoint for retrieving order tracking by Customer Request ID."
)
def track_customer_request_alias(
    customer_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return track_customer_request(customer_request_id, db, current_user)

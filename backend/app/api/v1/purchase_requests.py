from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.purchase_request import PurchaseRequestOut, RFQSendRequest
from app.schemas.response import SuccessResponse
from app.crud.purchase_request import (
    get_purchase_request_by_id,
    get_purchase_requests,
    send_rfq,
    format_pr_out,
)

router = APIRouter(prefix="/purchase", tags=["3. Purchase - Request (PR & RFQ)"])


@router.get(
    "/request",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="List Purchase Requests",
    description="Retrieve Purchase Requests with suppliers asked count, quotes received count, status, and pagination."
)
def list_prs(
    search: Optional[str] = Query(None, description="Search by PR number, CR number, or reference"),
    status: Optional[str] = Query("all", description="Filter by status ('Open', 'RFQ Sent', 'Quoted', 'Ordered', or 'all')"),
    eligible_for_quote: Optional[bool] = Query(None, description="Filter only PRs with sent RFQs ready for Vendor Quotations"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_purchase_requests(
        db, skip=skip, limit=limit, search=search, status=status, eligible_for_quote=eligible_for_quote
    )
    return SuccessResponse(
        success=True,
        message="Purchase requests retrieved successfully",
        data={
            "items": [format_pr_out(pr) for pr in items],
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    )


@router.get(
    "/request/{pr_id}",
    response_model=SuccessResponse[PurchaseRequestOut],
    summary="Get Purchase Request Details",
    description="Retrieve a single Purchase Request with item lines and RFQ supplier history."
)
def get_pr(
    pr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pr = get_purchase_request_by_id(db, pr_id)
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Purchase Request with ID {pr_id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Purchase request retrieved successfully",
        data=format_pr_out(pr),
    )


@router.post(
    "/rfq/send",
    response_model=SuccessResponse[PurchaseRequestOut],
    summary="Send RFQ to Suppliers",
    description=(
        "Dispatch Request for Quotation (RFQ) to multiple suppliers. "
        "Creates email log records, associates asked suppliers, and sets PR and CR statuses to 'RFQ Sent'."
    )
)
def dispatch_rfq(
    rfq_in: RFQSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        pr, logs = send_rfq(db, rfq_in)
        return SuccessResponse(
            success=True,
            message=f"RFQ dispatched successfully to {len(logs)} supplier(s).",
            data=format_pr_out(pr),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

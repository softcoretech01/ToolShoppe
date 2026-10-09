from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.customer_quotation import (
    CustomerQuotationOut, CustomerQuotationListOut, CustomerQuotationUpdate,
    CustomerQuotationSendRequest, CustomerQuotationResendRequest
)
from app.schemas.response import SuccessResponse
from app.crud.customer import get_customer_by_name
from app.crud.customer_quotation import (
    get_customer_quotation_by_id, get_customer_quotations,
    update_customer_quotation, send_customer_quotation,
    resend_customer_quotation, mark_quotation_accepted,
    mark_quotation_rejected, format_cq_out,
    auto_create_quotation_from_comparison
)

router = APIRouter(prefix="/sales/quotation", tags=["2. Sales - Quotation"])


@router.get(
    "",
    response_model=SuccessResponse[CustomerQuotationListOut],
    summary="List Customer Quotations",
    description="Retrieve list of customer quotations with optional filtering by status, customer, and pagination."
)
def list_quotations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status (Draft, Sent, Accepted, Rejected, Expired)"),
    customer_id: Optional[int] = Query(None, description="Filter by Customer ID"),
    customer_name: Optional[str] = Query(None, description="Filter by Customer Name"),
    request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if customer_id is None and customer_name:
        cust = get_customer_by_name(db, customer_name)
        if cust:
            customer_id = cust.id

    items, total = get_customer_quotations(
        db=db, skip=skip, limit=limit, status=status, customer_id=customer_id, request_id=request_id
    )
    data = CustomerQuotationListOut(
        total=total,
        items=[format_cq_out(cq) for cq in items],
    )
    return SuccessResponse(
        success=True,
        message="Customer quotations retrieved successfully.",
        data=data,
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[CustomerQuotationOut],
    summary="Get Customer Quotation Details",
    description="Retrieve details of a single Customer Quotation by its ID."
)
def get_quotation(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cq = get_customer_quotation_by_id(db, id)
    if not cq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer Quotation with ID {id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Customer quotation retrieved successfully.",
        data=format_cq_out(cq),
    )


@router.post(
    "/create-from-comparison/{comparison_id}",
    response_model=SuccessResponse[CustomerQuotationOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Quotation from Approved Comparison",
    description="Auto-creates customer quotation from an approved comparison with default markup and supplier rates."
)
def create_from_comparison(
    comparison_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cq = auto_create_quotation_from_comparison(db, comparison_id)
        return SuccessResponse(
            success=True,
            message="Customer quotation generated successfully.",
            data=format_cq_out(cq),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.put(
    "/{id}",
    response_model=SuccessResponse[CustomerQuotationOut],
    summary="Update Customer Quotation Prices / Dates",
    description="Update customer selling prices and valid_till date. Recalculates margins and line totals."
)
def update_quotation(
    id: int,
    obj_in: CustomerQuotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cq = update_customer_quotation(db, id, obj_in)
        return SuccessResponse(
            success=True,
            message="Customer quotation updated successfully.",
            data=format_cq_out(cq),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/send",
    response_model=SuccessResponse[CustomerQuotationOut],
    summary="Send Customer Quotation Email",
    description="Send customer quotation email. Updates status to 'Sent', logs email in EmailLog."
)
def send_quotation(
    send_in: CustomerQuotationSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not send_in.quotation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quotation_id is required in request payload.",
        )
    try:
        cq = send_customer_quotation(db, send_in.quotation_id, send_in)
        return SuccessResponse(
            success=True,
            message=f"Quotation {cq.quotation_no} sent successfully to customer.",
            data=format_cq_out(cq),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post(
    "/{id}/resend",
    response_model=SuccessResponse[CustomerQuotationOut],
    summary="Resend Customer Quotation Email",
    description="Resends customer quotation email and registers a new entry in the Email Log."
)
def resend_quotation(
    id: int,
    resend_in: CustomerQuotationResendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cq = resend_customer_quotation(db, id, resend_in)
        return SuccessResponse(
            success=True,
            message=f"Quotation {cq.quotation_no} resent successfully.",
            data=format_cq_out(cq),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.patch(
    "/{id}/accept",
    response_model=SuccessResponse[CustomerQuotationOut],
    summary="Mark Customer Quotation as Accepted",
    description="Marks quotation as 'Accepted'. This unlocks creation of the Customer PO."
)
def accept_quotation(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cq = mark_quotation_accepted(db, id)
        return SuccessResponse(
            success=True,
            message=f"Quotation {cq.quotation_no} accepted by customer.",
            data=format_cq_out(cq),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.patch(
    "/{id}/reject",
    response_model=SuccessResponse[CustomerQuotationOut],
    summary="Mark Customer Quotation as Rejected",
    description="Marks quotation as 'Rejected'. Rejected quotations cannot be converted to Customer PO."
)
def reject_quotation(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        cq = mark_quotation_rejected(db, id)
        return SuccessResponse(
            success=True,
            message=f"Quotation {cq.quotation_no} rejected by customer.",
            data=format_cq_out(cq),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

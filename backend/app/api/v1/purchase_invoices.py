"""
Purchase Invoice Management API Endpoints
Handles recording supplier purchase invoices against accepted Goods Receipt Notes (GRN).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.purchase_invoice import (
    PurchaseInvoiceCreate, PurchaseInvoiceOut, PurchaseInvoiceListOut
)
from app.schemas.response import SuccessResponse
from app.crud.purchase_invoice import (
    create_purchase_invoice, get_purchase_invoice_by_id,
    get_purchase_invoices, format_purchase_invoice_out
)

router = APIRouter(prefix="/purchase/invoices", tags=["3. Purchase - Invoice"])
api_alias_router = APIRouter(prefix="/api/purchase-invoices", tags=["3. Purchase - Invoice"])


@router.post(
    "",
    response_model=SuccessResponse[PurchaseInvoiceOut],
    status_code=status.HTTP_201_CREATED,
    summary="Record Purchase Invoice",
    description=(
        "Record a Supplier Purchase Invoice against an accepted GRN. "
        "Supplier invoice number and date are recorded, rejected quantities are excluded, "
        "and duplicate billing against the same GRN is prevented."
    ),
)
@api_alias_router.post(
    "",
    response_model=SuccessResponse[PurchaseInvoiceOut],
    status_code=status.HTTP_201_CREATED,
    summary="Record Purchase Invoice",
)
def record_invoice(
    invoice_in: PurchaseInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        invoice = create_purchase_invoice(db=db, obj_in=invoice_in, user_id=current_user.id)
        return SuccessResponse(
            success=True,
            message="Purchase Invoice recorded successfully.",
            data=format_purchase_invoice_out(invoice),
        )
    except ValueError as exc:
        msg = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=msg)


@router.get(
    "",
    response_model=SuccessResponse[PurchaseInvoiceListOut],
    summary="List Purchase Invoices",
    description="Retrieve paginated list of Purchase Invoices with optional filtering.",
)
@api_alias_router.get(
    "",
    response_model=SuccessResponse[PurchaseInvoiceListOut],
    summary="List Purchase Invoices",
)
def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status (Recorded)"),
    supplier_id: Optional[int] = Query(None, description="Filter by Supplier ID"),
    customer_request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    grn_id: Optional[int] = Query(None, description="Filter by GRN ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_purchase_invoices(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        supplier_id=supplier_id,
        customer_request_id=customer_request_id,
        grn_id=grn_id,
    )
    data = PurchaseInvoiceListOut(
        total=total,
        items=[format_purchase_invoice_out(inv) for inv in items],
    )
    return SuccessResponse(
        success=True,
        message="Purchase Invoices retrieved successfully.",
        data=data,
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[PurchaseInvoiceOut],
    summary="Get Purchase Invoice Details",
    description="Retrieve details and line items for a specific Purchase Invoice by ID.",
)
@api_alias_router.get(
    "/{id}",
    response_model=SuccessResponse[PurchaseInvoiceOut],
    summary="Get Purchase Invoice Details",
)
def get_invoice(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = get_purchase_invoice_by_id(db, id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Purchase Invoice with ID {id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Purchase Invoice retrieved successfully.",
        data=format_purchase_invoice_out(invoice),
    )

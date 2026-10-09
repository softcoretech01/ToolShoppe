"""
Sales Invoice Management API Endpoints
Handles customer invoicing generated from Outward delivery challans.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.sales_invoice import (
    SalesInvoiceCreate, SalesInvoiceOut, SalesInvoiceListOut, SalesInvoicePreviewOut
)
from app.schemas.response import SuccessResponse
from app.crud.sales_invoice import (
    create_sales_invoice, get_sales_invoice_by_id, get_sales_invoices,
    format_sales_invoice_out, preview_sales_invoice
)
from app.crud.outward import get_outward_by_id
from app.crud.customer import get_customer_by_name

router = APIRouter(prefix="/sales/invoices", tags=["2. Sales - Invoice"])
api_alias_router = APIRouter(prefix="/api/sales-invoices", tags=["2. Sales - Invoice"])


@router.post(
    "",
    response_model=SuccessResponse[SalesInvoiceOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Sales Invoice",
    description="Generate a Customer Sales Invoice from a posted Outward Delivery Challan.",
)
@api_alias_router.post(
    "",
    response_model=SuccessResponse[SalesInvoiceOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Sales Invoice",
)
def create_invoice(
    invoice_in: SalesInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        invoice = create_sales_invoice(db=db, obj_in=invoice_in, user_id=current_user.id)
        return SuccessResponse(
            success=True,
            message="Sales Invoice created successfully.",
            data=format_sales_invoice_out(invoice),
        )
    except ValueError as exc:
        msg = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=msg)


@router.get(
    "",
    response_model=SuccessResponse[SalesInvoiceListOut],
    summary="List Sales Invoices",
    description="Retrieve paginated list of Sales Invoices with optional filtering.",
)
@api_alias_router.get(
    "",
    response_model=SuccessResponse[SalesInvoiceListOut],
    summary="List Sales Invoices",
)
def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status (Issued, Created, Paid)"),
    customer_id: Optional[int] = Query(None, description="Filter by Customer ID"),
    customer_name: Optional[str] = Query(None, description="Filter by Customer Name"),
    customer_request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    outward_id: Optional[int] = Query(None, description="Filter by Outward ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if customer_id is None and customer_name:
        cust = get_customer_by_name(db, customer_name)
        if cust:
            customer_id = cust.id

    items, total = get_sales_invoices(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        customer_id=customer_id,
        customer_request_id=customer_request_id,
        outward_id=outward_id,
    )
    data = SalesInvoiceListOut(
        total=total,
        items=[format_sales_invoice_out(inv) for inv in items],
    )
    return SuccessResponse(
        success=True,
        message="Sales Invoices retrieved successfully.",
        data=data,
    )


@router.get(
    "/{id}/preview",
    response_model=SuccessResponse[SalesInvoicePreviewOut],
    summary="Preview Sales Invoice",
    description="Preview invoice line items, tax breakdown, and grand total for an Outward ID (or existing invoice).",
)
@api_alias_router.get(
    "/{id}/preview",
    response_model=SuccessResponse[SalesInvoicePreviewOut],
    summary="Preview Sales Invoice",
)
def preview_invoice(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        outward = get_outward_by_id(db, id)
        if outward:
            preview_data = preview_sales_invoice(db, id)
        else:
            invoice = get_sales_invoice_by_id(db, id)
            if not invoice:
                raise ValueError(f"Outward or Sales Invoice with ID {id} not found.")
            preview_data = preview_sales_invoice(db, invoice.outward_id)

        return SuccessResponse(
            success=True,
            message="Sales Invoice preview generated successfully.",
            data=preview_data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{id}",
    response_model=SuccessResponse[SalesInvoiceOut],
    summary="Get Sales Invoice Details",
    description="Retrieve details and line items for a specific Sales Invoice by ID.",
)
@api_alias_router.get(
    "/{id}",
    response_model=SuccessResponse[SalesInvoiceOut],
    summary="Get Sales Invoice Details",
)
def get_invoice(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = get_sales_invoice_by_id(db, id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales Invoice with ID {id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Sales Invoice retrieved successfully.",
        data=format_sales_invoice_out(invoice),
    )

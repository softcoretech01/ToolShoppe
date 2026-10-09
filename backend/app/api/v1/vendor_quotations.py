from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.vendor_quotation import (
    VendorQuotationCreate, VendorQuotationUpdate, VendorQuotationOut
)
from app.schemas.response import SuccessResponse
from app.crud.vendor_quotation import (
    get_vendor_quotation_by_id,
    get_vendor_quotations,
    create_vendor_quotation,
    update_vendor_quotation,
    format_vq_out,
)

router = APIRouter(prefix="/purchase/vendor-quotation", tags=["3. Purchase - Vendor Quotation"])


@router.post(
    "",
    response_model=SuccessResponse[VendorQuotationOut],
    status_code=status.HTTP_201_CREATED,
    summary="Record Vendor Quotation",
    description=(
        "Record a supplier's response to an RFQ. "
        "Automatically calculates line totals, subtotal, GST tax, and grand total. "
        "Enforces single quotation per supplier per Purchase Request."
    )
)
def create_vq(
    vq_in: VendorQuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        vq = create_vendor_quotation(db, vq_in)
        return SuccessResponse(
            success=True,
            message="Vendor quotation recorded successfully.",
            data=format_vq_out(vq, db),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="List Vendor Quotations",
    description="Retrieve Vendor Quotations with optional filters by Purchase Request, Supplier, or status."
)
def list_vqs(
    pr_id: Optional[int] = Query(None, description="Filter by Purchase Request ID"),
    supplier_id: Optional[int] = Query(None, description="Filter by Supplier ID"),
    status: Optional[str] = Query("all", description="Filter by status ('Received', 'Selected', 'Rejected', or 'all')"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_vendor_quotations(
        db, skip=skip, limit=limit, pr_id=pr_id, supplier_id=supplier_id, status=status
    )
    return SuccessResponse(
        success=True,
        message="Vendor quotations retrieved successfully",
        data={
            "items": [format_vq_out(vq, db) for vq in items],
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    )


@router.get(
    "/{vq_id}",
    response_model=SuccessResponse[VendorQuotationOut],
    summary="Get Vendor Quotation Details",
    description="Retrieve a single Vendor Quotation with item rates and calculations."
)
def get_vq(
    vq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vq = get_vendor_quotation_by_id(db, vq_id)
    if not vq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor Quotation with ID {vq_id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Vendor quotation retrieved successfully",
        data=format_vq_out(vq, db),
    )


@router.put(
    "/{vq_id}",
    response_model=SuccessResponse[VendorQuotationOut],
    summary="Update Vendor Quotation",
    description="Update terms, freight, or line rates of an existing Vendor Quotation."
)
def update_vq(
    vq_id: int,
    vq_in: VendorQuotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vq = get_vendor_quotation_by_id(db, vq_id)
    if not vq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor Quotation with ID {vq_id} not found.",
        )

    updated = update_vendor_quotation(db, vq, vq_in)
    return SuccessResponse(
        success=True,
        message="Vendor quotation updated successfully",
        data=format_vq_out(updated, db),
    )

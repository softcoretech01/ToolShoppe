from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.purchase_order import (
    PurchaseOrderOut, PurchaseOrderListOut, PurchaseOrderSendRequest
)
from app.schemas.response import SuccessResponse
from app.crud.purchase_order import (
    get_purchase_order_by_id, get_purchase_orders, send_purchase_order, format_po_out
)

router = APIRouter(prefix="/purchase/purchase-order", tags=["3. Purchase - Purchase Order (PO)"])


@router.get(
    "",
    response_model=SuccessResponse[PurchaseOrderListOut],
    summary="List Supplier Purchase Orders",
    description="Retrieve list of supplier purchase orders with pagination and optional filters."
)
def list_purchase_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status (Draft, Sent)"),
    supplier_id: Optional[int] = Query(None, description="Filter by Supplier ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_purchase_orders(
        db=db, skip=skip, limit=limit, status=status, supplier_id=supplier_id
    )
    data = PurchaseOrderListOut(
        total=total,
        items=[format_po_out(po) for po in items],
    )
    return SuccessResponse(
        success=True,
        message="Purchase orders retrieved successfully.",
        data=data,
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[PurchaseOrderOut],
    summary="Get Supplier Purchase Order Details",
    description="Retrieve details of a single Supplier Purchase Order by its ID."
)
def get_order(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = get_purchase_order_by_id(db, id)
    if not po:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Purchase Order with ID {id} not found.",
        )
    return SuccessResponse(
        success=True,
        message="Purchase order retrieved successfully.",
        data=format_po_out(po),
    )


@router.post(
    "/{id}/send",
    response_model=SuccessResponse[PurchaseOrderOut],
    summary="Send Supplier Purchase Order Email",
    description="Sends Purchase Order email to the supplier, registers email in EmailLog, and updates status to 'Sent'."
)
def send_order(
    id: int,
    send_in: PurchaseOrderSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        po = send_purchase_order(db, id, send_in)
        return SuccessResponse(
            success=True,
            message=f"Purchase order {po.po_no} dispatched to supplier successfully.",
            data=format_po_out(po),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.email_log import EmailLog
from app.schemas.purchase_order import (
    PurchaseOrderOut, PurchaseOrderItemOut, PurchaseOrderSendRequest
)
from app.core.email import send_live_email


def format_po_out(po: PurchaseOrder) -> PurchaseOrderOut:
    """Convert PurchaseOrder ORM model to schema."""
    lines_out = []
    for line in po.items:
        lines_out.append(
            PurchaseOrderItemOut(
                id=line.id,
                purchase_order_id=line.purchase_order_id,
                item_id=line.item_id,
                item_name=line.item.name if line.item else None,
                item_code=line.item.item_code if line.item else None,
                quantity=line.quantity,
                purchase_rate=line.purchase_rate,
                line_total=line.line_total,
            )
        )

    co = po.customer_order
    cr = co.customer_request if co else None
    cq = po.quotation
    sup = po.supplier

    return PurchaseOrderOut(
        id=po.id,
        po_no=po.po_no,
        customer_order_id=po.customer_order_id,
        customer_order_no=co.order_no if co else None,
        customer_po_number=co.customer_po_number if co else None,
        customer_request_id=cr.id if cr else None,
        customer_request_no=cr.request_no if cr else None,
        supplier_id=po.supplier_id,
        supplier_name=sup.name if sup else None,
        supplier_email=sup.email if sup else None,
        quotation_id=po.quotation_id,
        quotation_no=cq.quotation_no if cq else None,
        delivery_date=po.delivery_date,
        status=po.status,
        sent_at=po.sent_at,
        subtotal=po.subtotal,
        tax=po.tax,
        grand_total=po.grand_total,
        created_at=po.created_at,
        items=lines_out,
    )


def get_purchase_order_by_id(db: Session, po_id: int) -> Optional[PurchaseOrder]:
    """Retrieve Supplier Purchase Order by ID."""
    return db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()


def get_purchase_orders(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
) -> Tuple[List[PurchaseOrder], int]:
    """Retrieve Supplier Purchase Orders with optional filters and pagination."""
    query = db.query(PurchaseOrder)

    if status and status.lower() != "all":
        query = query.filter(PurchaseOrder.status.ilike(status.strip()))
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)

    total = query.count()
    items = query.order_by(PurchaseOrder.id.desc()).offset(skip).limit(limit).all()
    return items, total


def send_purchase_order(
    db: Session,
    po_id: int,
    obj_in: PurchaseOrderSendRequest
) -> PurchaseOrder:
    """
    Send Purchase Order to Supplier:
    - Validates supplier email.
    - Dispatches email via SMTP.
    - Saves entry in EmailLog with status & error details.
    - Sets status = 'Sent' upon success.
    """
    po = get_purchase_order_by_id(db, po_id)
    if not po:
        raise ValueError(f"Purchase Order with ID {po_id} not found.")

    recipient = (obj_in.recipient or (po.supplier.email if po.supplier else "")).strip()
    if not recipient:
        raise ValueError("Supplier recipient email address is required.")

    subject = obj_in.subject or f"Purchase Order {po.po_no} - ToolShoppe ERP"
    body = obj_in.body or f"Dear Supplier, Please find attached our Purchase Order {po.po_no}."

    delivery_res = send_live_email(recipients=recipient, subject=subject, body=body)

    now = datetime.utcnow()
    email_log = EmailLog(
        document_type="Purchase Order",
        document_id=po.id,
        recipient=recipient,
        subject=subject,
        body=body,
        status=delivery_res.status,
        error_message=delivery_res.error_message,
        sent_at=now,
    )
    db.add(email_log)

    if delivery_res.status == "Failed":
        db.commit()
        raise ValueError(f"Failed to dispatch purchase order email to supplier: {delivery_res.error_message}")

    po.status = "Sent"
    po.sent_at = now

    db.commit()
    db.refresh(po)
    return po

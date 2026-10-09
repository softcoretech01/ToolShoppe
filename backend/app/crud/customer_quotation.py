from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.customer_quotation import CustomerQuotation, CustomerQuotationItem
from app.models.quotation_comparison import QuotationComparison
from app.models.vendor_quotation import VendorQuotation
from app.models.customer_request import CustomerRequestItem
from app.models.email_log import EmailLog
from app.schemas.customer_quotation import (
    CustomerQuotationOut, CustomerQuotationItemOut, CustomerQuotationUpdate,
    CustomerQuotationSendRequest, CustomerQuotationResendRequest
)
from app.utils.pricing import compute_customer_price, compute_margin_pct, round_decimal
from app.core.email import send_live_email


def generate_cq_code(db: Session) -> str:
    """Generate next sequential Customer Quotation code (e.g. CQ-001)."""
    last = db.query(CustomerQuotation).order_by(CustomerQuotation.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"CQ-{next_num:03d}"
        if not db.query(CustomerQuotation).filter(CustomerQuotation.quotation_no == code).first():
            return code
        next_num += 1


def format_cq_out(cq: CustomerQuotation) -> CustomerQuotationOut:
    """Convert CustomerQuotation ORM model to schema."""
    lines_out = []
    for line in cq.items:
        lines_out.append(
            CustomerQuotationItemOut(
                id=line.id,
                quotation_id=line.quotation_id,
                item_id=line.item_id,
                item_name=line.item.name if line.item else None,
                item_code=line.item.item_code if line.item else None,
                supplier_rate=line.supplier_rate,
                customer_price=line.customer_price,
                quantity=line.quantity,
                margin_percent=line.margin_percent,
                line_total=line.line_total,
            )
        )

    cr = cq.customer_request
    cust = cq.customer
    sup = cq.supplier

    return CustomerQuotationOut(
        id=cq.id,
        quotation_no=cq.quotation_no,
        customer_request_id=cq.customer_request_id,
        customer_request_no=cr.request_no if cr else None,
        comparison_id=cq.comparison_id,
        customer_id=cq.customer_id,
        customer_name=cust.name if cust else None,
        customer_email=cust.email if cust else None,
        supplier_id=cq.supplier_id,
        supplier_name=sup.name if sup else None,
        valid_till=cq.valid_till,
        subtotal=cq.subtotal,
        tax=cq.tax,
        grand_total=cq.grand_total,
        status=cq.status,
        sent_at=cq.sent_at,
        created_at=cq.created_at,
        items=lines_out,
    )


def auto_create_quotation_from_comparison(db: Session, comparison_id: int) -> CustomerQuotation:
    """
    Auto create quotation from approved comparison.
    - Uses approved supplier rates as Cost.
    - Applies customer's default markup (or 15%).
    - Calculates live margin percent and line totals.
    - Sets initial status to 'Draft'.
    """
    qc = db.query(QuotationComparison).filter(QuotationComparison.id == comparison_id).first()
    if not qc:
        raise ValueError(f"Quotation Comparison with ID {comparison_id} not found.")

    if qc.status != "Approved" or not qc.approved_supplier_id:
        raise ValueError("Customer quotation can only be created from an approved comparison.")

    # Check if quotation already exists for this comparison
    existing = db.query(CustomerQuotation).filter(CustomerQuotation.comparison_id == comparison_id).first()
    if existing:
        return existing

    pr = qc.purchase_request
    if not pr or not pr.customer_request:
        raise ValueError("Comparison must have an associated purchase request and customer request.")

    cr = pr.customer_request
    customer = cr.customer
    default_markup = customer.default_markup if (customer and customer.default_markup and customer.default_markup > 0) else Decimal("15.00")

    # Winning vendor quotation
    vq = db.query(VendorQuotation).filter(
        VendorQuotation.purchase_request_id == pr.id,
        VendorQuotation.supplier_id == qc.approved_supplier_id
    ).first()
    if not vq:
        raise ValueError("Winning vendor quotation not found for approved supplier.")

    # Map item quantities from customer request
    qty_map = {item.item_id: item.quantity for item in cr.items} if cr.items else {}

    cq_code = generate_cq_code(db)
    valid_till = date.today() + timedelta(days=15)

    cq = CustomerQuotation(
        quotation_no=cq_code,
        customer_request_id=cr.id,
        comparison_id=qc.id,
        customer_id=customer.id if customer else cr.customer_id,
        supplier_id=qc.approved_supplier_id,
        valid_till=valid_till,
        subtotal=Decimal("0.00"),
        tax=Decimal("0.00"),
        grand_total=Decimal("0.00"),
        status="Draft",
    )
    db.add(cq)
    db.flush()

    subtotal = Decimal("0.00")
    for vq_item in vq.items:
        if vq_item.not_quoted or vq_item.rate <= 0:
            continue
        qty = qty_map.get(vq_item.item_id, Decimal("1.00"))
        supplier_rate = round_decimal(vq_item.rate, 2)
        customer_price = compute_customer_price(supplier_rate, default_markup)
        margin_pct = compute_margin_pct(customer_price, supplier_rate)
        line_total = round_decimal(customer_price * qty, 2)
        subtotal += line_total

        cq_item = CustomerQuotationItem(
            quotation_id=cq.id,
            item_id=vq_item.item_id,
            supplier_rate=supplier_rate,
            customer_price=customer_price,
            quantity=qty,
            margin_percent=margin_pct,
            line_total=line_total,
        )
        db.add(cq_item)

    tax = round_decimal(subtotal * Decimal("0.18"), 2)
    cq.subtotal = round_decimal(subtotal, 2)
    cq.tax = tax
    cq.grand_total = round_decimal(subtotal + tax, 2)

    db.commit()
    db.refresh(cq)
    return cq


def get_customer_quotation_by_id(db: Session, quotation_id: int) -> Optional[CustomerQuotation]:
    """Retrieve Customer Quotation by ID."""
    return db.query(CustomerQuotation).filter(CustomerQuotation.id == quotation_id).first()


def get_customer_quotations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    request_id: Optional[int] = None,
) -> Tuple[List[CustomerQuotation], int]:
    """Retrieve Customer Quotations with optional filters and pagination."""
    query = db.query(CustomerQuotation)

    if status and status.lower() != "all":
        query = query.filter(CustomerQuotation.status.ilike(status.strip()))
    if customer_id:
        query = query.filter(CustomerQuotation.customer_id == customer_id)
    if request_id:
        query = query.filter(CustomerQuotation.customer_request_id == request_id)

    total = query.count()
    items = query.order_by(CustomerQuotation.id.desc()).offset(skip).limit(limit).all()
    return items, total


def update_customer_quotation(
    db: Session,
    quotation_id: int,
    obj_in: CustomerQuotationUpdate
) -> CustomerQuotation:
    """
    Update Customer Quotation:
    - Edit customer selling price per line (recalculates margin % and line total).
    - Supplier rate is read-only.
    - Margin formula: ((Selling Price - Cost) / Selling Price) * 100.
    - Valid till date editable.
    """
    cq = get_customer_quotation_by_id(db, quotation_id)
    if not cq:
        raise ValueError(f"Customer Quotation with ID {quotation_id} not found.")

    if cq.status in ["Accepted", "Rejected", "Expired"]:
        raise ValueError(f"Cannot edit quotation with status '{cq.status}'.")

    if obj_in.valid_till:
        cq.valid_till = obj_in.valid_till

    if obj_in.items:
        price_map = {item.item_id: item.customer_price for item in obj_in.items}
        subtotal = Decimal("0.00")
        for line in cq.items:
            if line.item_id in price_map:
                new_price = round_decimal(price_map[line.item_id], 2)
                line.customer_price = new_price
                line.margin_percent = compute_margin_pct(new_price, line.supplier_rate)
                line.line_total = round_decimal(new_price * line.quantity, 2)
            subtotal += line.line_total

        cq.subtotal = round_decimal(subtotal, 2)
        cq.tax = round_decimal(subtotal * Decimal("0.18"), 2)
        cq.grand_total = round_decimal(cq.subtotal + cq.tax, 2)

    db.commit()
    db.refresh(cq)
    return cq


def send_customer_quotation(
    db: Session,
    quotation_id: int,
    obj_in: CustomerQuotationSendRequest
) -> CustomerQuotation:
    """
    Send Customer Quotation:
    - Sets status = 'Sent'.
    - Records sent_at.
    - Saves entry in EmailLog (document_type = 'Customer Quotation').
    """
    cq = get_customer_quotation_by_id(db, quotation_id)
    if not cq:
        raise ValueError(f"Customer Quotation with ID {quotation_id} not found.")

    recipient = (obj_in.recipient or (cq.customer.email if cq.customer else "")).strip()
    if not recipient:
        raise ValueError("Recipient email address is required.")

    delivery_res = send_live_email(recipients=recipient, subject=obj_in.subject, body=obj_in.body)

    now = datetime.utcnow()
    email_log = EmailLog(
        document_type="Customer Quotation",
        document_id=cq.id,
        recipient=recipient,
        subject=obj_in.subject,
        body=obj_in.body,
        status=delivery_res.status,
        error_message=delivery_res.error_message,
        sent_at=now,
    )
    db.add(email_log)

    if delivery_res.status == "Failed":
        db.commit()
        raise ValueError(f"Failed to deliver customer quotation email: {delivery_res.error_message}")

    cq.status = "Sent"
    cq.sent_at = now

    db.commit()
    db.refresh(cq)
    return cq


def resend_customer_quotation(
    db: Session,
    quotation_id: int,
    obj_in: CustomerQuotationResendRequest
) -> CustomerQuotation:
    """
    Resend Customer Quotation:
    - Dispatches email via SMTP.
    - Saves new entry in EmailLog (document_type = 'Customer Quotation') with status & error details.
    - Status remains 'Sent' (or updates if Draft/Expired).
    """
    cq = get_customer_quotation_by_id(db, quotation_id)
    if not cq:
        raise ValueError(f"Customer Quotation with ID {quotation_id} not found.")

    recipient = (obj_in.recipient or (cq.customer.email if cq.customer else "")).strip()
    if not recipient:
        raise ValueError("Recipient email address is required.")

    subject = obj_in.subject or f"Quotation {cq.quotation_no} - ToolShoppe ERP"
    body = obj_in.body or f"Dear Customer, Please find attached quotation {cq.quotation_no}."

    delivery_res = send_live_email(recipients=recipient, subject=subject, body=body)

    now = datetime.utcnow()
    email_log = EmailLog(
        document_type="Customer Quotation",
        document_id=cq.id,
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
        raise ValueError(f"Failed to deliver customer quotation email: {delivery_res.error_message}")

    cq.status = "Sent"
    cq.sent_at = now

    db.commit()
    db.refresh(cq)
    return cq


def mark_quotation_accepted(db: Session, quotation_id: int) -> CustomerQuotation:
    """Mark Customer Quotation as Accepted."""
    cq = get_customer_quotation_by_id(db, quotation_id)
    if not cq:
        raise ValueError(f"Customer Quotation with ID {quotation_id} not found.")

    if cq.status == "Rejected":
        raise ValueError("A rejected quotation cannot be marked as accepted.")

    cq.status = "Accepted"
    db.commit()
    db.refresh(cq)
    return cq


def mark_quotation_rejected(db: Session, quotation_id: int) -> CustomerQuotation:
    """Mark Customer Quotation as Rejected."""
    cq = get_customer_quotation_by_id(db, quotation_id)
    if not cq:
        raise ValueError(f"Customer Quotation with ID {quotation_id} not found.")

    cq.status = "Rejected"
    db.commit()
    db.refresh(cq)
    return cq

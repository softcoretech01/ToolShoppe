import re
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.sales_invoice import SalesInvoice, SalesInvoiceItem
from app.models.purchase_invoice import PurchaseInvoice
from app.models.outward import Outward, OutwardItem
from app.models.customer_order import CustomerOrder
from app.models.customer_request import CustomerRequest
from app.models.customer import Customer
from app.models.item import Item
from app.crud.customer import get_customer_by_name
from app.crud.item import get_item_by_name
from app.schemas.sales_invoice import (
    SalesInvoiceCreate, SalesInvoiceOut, SalesInvoiceItemOut,
    SalesInvoicePreviewOut
)


def generate_sales_invoice_code(db: Session) -> str:
    """Generate next sequential Sales Invoice code (e.g. SI-0001)."""
    last = db.query(SalesInvoice).order_by(SalesInvoice.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"SI-{next_num:04d}"
        if not db.query(SalesInvoice).filter(SalesInvoice.invoice_no == code).first():
            return code
        next_num += 1


def parse_payment_terms_days(terms: Optional[str]) -> int:
    """Extract payment term days from strings like '30 days', '45 Days', etc."""
    if not terms:
        return 30
    match = re.search(r"(\d+)", terms)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return 30
    return 30


def check_and_update_customer_request_status(db: Session, cr_id: int) -> None:
    """
    Evaluate Customer Request status progression:
    - If Outward posted AND both Sales Invoice and Purchase Invoice exist: 'Completed'.
    - If Outward posted AND Sales Invoice exists (but Purchase Invoice missing): 'Invoiced'.
    """
    cr = db.query(CustomerRequest).filter(CustomerRequest.id == cr_id).first()
    if not cr:
        return

    outward_exists = (
        db.query(Outward)
        .filter(Outward.customer_request_id == cr_id, Outward.status != "Draft")
        .first() is not None
    )

    has_sales_invoice = (
        db.query(SalesInvoice).filter(SalesInvoice.customer_request_id == cr_id).first() is not None
    )
    has_purchase_invoice = (
        db.query(PurchaseInvoice).filter(PurchaseInvoice.customer_request_id == cr_id).first() is not None
    )

    if outward_exists and has_sales_invoice and has_purchase_invoice:
        cr.status = "Completed"
    elif outward_exists and has_sales_invoice:
        cr.status = "Invoiced"


def format_sales_invoice_out(inv: SalesInvoice) -> SalesInvoiceOut:
    """Convert SalesInvoice model to Pydantic schema."""
    lines_out = []
    for line in inv.items:
        lines_out.append(
            SalesInvoiceItemOut(
                id=line.id,
                sales_invoice_id=line.sales_invoice_id,
                item_id=line.item_id,
                item_name=line.item.name if line.item else None,
                item_code=line.item.item_code if line.item else None,
                quantity=line.quantity,
                unit=line.unit,
                rate=line.rate,
                tax_percent=line.tax_percent,
                taxable_value=line.taxable_value,
                tax_amount=line.tax_amount,
                line_total=line.line_total,
            )
        )

    outw = inv.outward
    so = inv.customer_order
    cr = inv.customer_request
    cust = inv.customer

    return SalesInvoiceOut(
        id=inv.id,
        invoice_no=inv.invoice_no,
        outward_id=inv.outward_id,
        outward_no=outw.outward_no if outw else None,
        customer_order_id=inv.customer_order_id,
        customer_order_no=so.order_no if so else None,
        customer_request_id=inv.customer_request_id,
        customer_request_no=cr.request_no if cr else None,
        customer_id=inv.customer_id,
        customer_name=cust.name if cust else None,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        payment_terms=inv.payment_terms,
        subtotal=inv.subtotal,
        tax_amount=inv.tax_amount,
        grand_total=inv.grand_total,
        status=inv.status,
        remarks=inv.remarks,
        created_at=inv.created_at,
        items=lines_out,
    )


def get_sales_invoice_by_id(db: Session, invoice_id: int) -> Optional[SalesInvoice]:
    """Retrieve Sales Invoice by ID."""
    return db.query(SalesInvoice).filter(SalesInvoice.id == invoice_id).first()


def get_sales_invoices(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    customer_request_id: Optional[int] = None,
    outward_id: Optional[int] = None,
) -> Tuple[List[SalesInvoice], int]:
    """Retrieve Sales Invoices with filters and pagination."""
    query = db.query(SalesInvoice)

    if status and status.lower() != "all":
        query = query.filter(SalesInvoice.status.ilike(status.strip()))
    if customer_id:
        query = query.filter(SalesInvoice.customer_id == customer_id)
    if customer_request_id:
        query = query.filter(SalesInvoice.customer_request_id == customer_request_id)
    if outward_id:
        query = query.filter(SalesInvoice.outward_id == outward_id)

    total = query.count()
    items = query.order_by(SalesInvoice.id.desc()).offset(skip).limit(limit).all()
    return items, total


def preview_sales_invoice(db: Session, outward_id: int) -> SalesInvoicePreviewOut:
    """Generate preview calculation for an Outward document without persisting."""
    outward = db.query(Outward).filter(Outward.id == outward_id).first()
    if not outward:
        raise ValueError(f"Outward with ID {outward_id} not found.")

    cust = outward.customer
    terms = cust.payment_terms if cust and cust.payment_terms else "30 Days"
    inv_date = date.today()
    days = parse_payment_terms_days(terms)
    due_date = inv_date + timedelta(days=days)

    lines_out: List[SalesInvoiceItemOut] = []
    subtotal = Decimal("0.00")
    total_tax = Decimal("0.00")

    for out_item in outward.items:
        qty = out_item.dispatched_qty
        rate = out_item.unit_price
        tax_pct = out_item.item.tax_percent if out_item.item else Decimal("18.00")
        taxable = (qty * rate).quantize(Decimal("0.01"))
        tax = (taxable * (tax_pct / Decimal("100.00"))).quantize(Decimal("0.01"))
        line_tot = taxable + tax

        subtotal += taxable
        total_tax += tax

        lines_out.append(
            SalesInvoiceItemOut(
                id=0,
                sales_invoice_id=0,
                item_id=out_item.item_id,
                item_name=out_item.item.name if out_item.item else None,
                item_code=out_item.item.item_code if out_item.item else None,
                quantity=qty,
                unit=out_item.unit or "Nos",
                rate=rate,
                tax_percent=tax_pct,
                taxable_value=taxable,
                tax_amount=tax,
                line_total=line_tot,
            )
        )

    grand_total = subtotal + total_tax

    return SalesInvoicePreviewOut(
        outward_id=outward.id,
        outward_no=outward.outward_no,
        customer_id=outward.customer_id,
        customer_name=cust.name if cust else None,
        invoice_date=inv_date,
        due_date=due_date,
        payment_terms=terms,
        subtotal=subtotal,
        tax_amount=total_tax,
        grand_total=grand_total,
        items=lines_out,
    )


def create_sales_invoice(db: Session, obj_in: SalesInvoiceCreate, user_id: Optional[int] = None) -> SalesInvoice:
    """
    Create a Sales Invoice from an Outward document:
    1. Validate Outward exists and is posted (not Draft).
    2. Enforce duplicate protection: Outward must not have already been invoiced.
    3. Inherit payment terms and calculate due date.
    4. Validate and calculate line items (taxable value, tax amount, line total).
    5. Update Outward status to 'Invoiced'.
    6. Check and update Customer Request status (to 'Invoiced' or 'Completed').
    """
    outward = db.query(Outward).filter(Outward.id == obj_in.outward_id).first()
    if not outward:
        raise ValueError(f"Outward with ID {obj_in.outward_id} not found.")

    if outward.status == "Draft":
        outward.status = "Dispatched"

    # Duplicate invoicing protection - reject if already invoiced
    existing_invoice = db.query(SalesInvoice).filter(SalesInvoice.outward_id == outward.id).first()
    if existing_invoice:
        raise ValueError(f"Cannot create invoice. Outward document {outward.outward_no} has already been invoiced.")

    so = outward.customer_order
    cr_id = outward.customer_request_id
    cust = outward.customer

    cust_id = obj_in.customer_id
    if not cust_id and obj_in.customer_name:
        c_obj = get_customer_by_name(db, obj_in.customer_name)
        if c_obj:
            cust_id = c_obj.id
    if not cust_id:
        cust_id = outward.customer_id

    inv_date = obj_in.invoice_date or date.today()

    terms = obj_in.payment_terms or (cust.payment_terms if cust and cust.payment_terms else "30 Days")
    if obj_in.due_date:
        due_date = obj_in.due_date
    else:
        days = parse_payment_terms_days(terms)
        due_date = inv_date + timedelta(days=days)

    invoice_no = generate_sales_invoice_code(db)

    sales_inv = SalesInvoice(
        invoice_no=invoice_no,
        outward_id=outward.id,
        customer_order_id=so.id,
        customer_request_id=cr_id,
        customer_id=cust_id,
        invoice_date=inv_date,
        due_date=due_date,
        payment_terms=terms,
        subtotal=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        grand_total=Decimal("0.00"),
        status="Issued",
        remarks=obj_in.remarks,
        created_by=user_id,
    )
    db.add(sales_inv)
    db.flush()

    out_items_map = {item.item_id: item for item in outward.items}
    lines_to_process = obj_in.items if (obj_in.items and len(obj_in.items) > 0) else None

    subtotal = Decimal("0.00")
    total_tax = Decimal("0.00")

    if lines_to_process:
        for line in lines_to_process:
            if line.item_id is None and line.item_name:
                itm_obj = get_item_by_name(db, line.item_name)
                if itm_obj:
                    line.item_id = itm_obj.id
            if line.item_id not in out_items_map:
                raise ValueError(f"Item ID {line.item_id} is not present in Outward {outward.outward_no}.")
            out_item = out_items_map[line.item_id]
            if line.quantity > out_item.dispatched_qty:
                raise ValueError(
                    f"Invoice quantity ({line.quantity}) cannot exceed outward dispatched quantity "
                    f"({out_item.dispatched_qty}) for item ID {line.item_id}."
                )

            rate = line.rate if line.rate is not None else out_item.unit_price
            tax_pct = line.tax_percent if line.tax_percent is not None else (
                out_item.item.tax_percent if out_item.item else Decimal("18.00")
            )
            taxable = (line.quantity * rate).quantize(Decimal("0.01"))
            tax = (taxable * (tax_pct / Decimal("100.00"))).quantize(Decimal("0.01"))
            line_tot = taxable + tax

            subtotal += taxable
            total_tax += tax

            inv_item = SalesInvoiceItem(
                sales_invoice_id=sales_inv.id,
                item_id=line.item_id,
                quantity=line.quantity,
                unit=line.unit or out_item.unit or "Nos",
                rate=rate,
                tax_percent=tax_pct,
                taxable_value=taxable,
                tax_amount=tax,
                line_total=line_tot,
            )
            db.add(inv_item)
    else:
        for out_item in outward.items:
            qty = out_item.dispatched_qty
            rate = out_item.unit_price
            tax_pct = out_item.item.tax_percent if out_item.item else Decimal("18.00")
            taxable = (qty * rate).quantize(Decimal("0.01"))
            tax = (taxable * (tax_pct / Decimal("100.00"))).quantize(Decimal("0.01"))
            line_tot = taxable + tax

            subtotal += taxable
            total_tax += tax

            inv_item = SalesInvoiceItem(
                sales_invoice_id=sales_inv.id,
                item_id=out_item.item_id,
                quantity=qty,
                unit=out_item.unit or "Nos",
                rate=rate,
                tax_percent=tax_pct,
                taxable_value=taxable,
                tax_amount=tax,
                line_total=line_tot,
            )
            db.add(inv_item)

    sales_inv.subtotal = subtotal
    sales_inv.tax_amount = total_tax
    sales_inv.grand_total = subtotal + total_tax

    # Update Outward status to 'Invoiced'
    outward.status = "Invoiced"

    # Evaluate order completion / request status
    check_and_update_customer_request_status(db, cr_id)

    db.commit()
    db.refresh(sales_inv)
    return sales_inv

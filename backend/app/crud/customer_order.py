from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.customer_order import CustomerOrder, CustomerOrderItem
from app.models.customer_quotation import CustomerQuotation
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.vendor_quotation import VendorQuotation
from app.models.quotation_comparison import QuotationComparison
from app.models.customer_request import CustomerRequest
from app.schemas.customer_order import (
    CustomerOrderCreate, CustomerOrderOut, CustomerOrderItemOut
)
from app.utils.pricing import round_decimal


def generate_co_code(db: Session) -> str:
    """Generate next sequential Customer Order code (e.g. SO-001)."""
    last = db.query(CustomerOrder).order_by(CustomerOrder.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"SO-{next_num:03d}"
        if not db.query(CustomerOrder).filter(CustomerOrder.order_no == code).first():
            return code
        next_num += 1


def generate_po_code(db: Session) -> str:
    """Generate next sequential Purchase Order code (e.g. PO-001)."""
    last = db.query(PurchaseOrder).order_by(PurchaseOrder.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"PO-{next_num:03d}"
        if not db.query(PurchaseOrder).filter(PurchaseOrder.po_no == code).first():
            return code
        next_num += 1


def format_co_out(co: CustomerOrder) -> CustomerOrderOut:
    """Convert CustomerOrder ORM model to schema."""
    lines_out = []
    for line in co.items:
        lines_out.append(
            CustomerOrderItemOut(
                id=line.id,
                order_id=line.order_id,
                item_id=line.item_id,
                item_name=line.item.name if line.item else None,
                item_code=line.item.item_code if line.item else None,
                quantity=line.quantity,
                selling_price=line.selling_price,
                line_total=line.line_total,
            )
        )

    cr = co.customer_request
    cq = co.quotation
    cust = cr.customer if cr else (cq.customer if cq else None)
    auto_po = co.purchase_orders[0] if co.purchase_orders else None

    return CustomerOrderOut(
        id=co.id,
        order_no=co.order_no,
        customer_request_id=co.customer_request_id,
        customer_request_no=cr.request_no if cr else None,
        quotation_id=co.quotation_id,
        quotation_no=cq.quotation_no if cq else None,
        customer_id=cust.id if cust else None,
        customer_name=cust.name if cust else None,
        customer_po_number=co.customer_po_number,
        po_date=co.po_date,
        delivery_date=co.delivery_date,
        status=co.status,
        created_at=co.created_at,
        items=lines_out,
        auto_purchase_order_id=auto_po.id if auto_po else None,
        auto_purchase_order_no=auto_po.po_no if auto_po else None,
    )


def create_customer_order(db: Session, obj_in: CustomerOrderCreate) -> CustomerOrder:
    """
    Create Customer Purchase Order (Sales Order):
    - Must be created from an accepted quotation (Rule 5).
    - Stores customer PO number, PO date, delivery date, quantities, and selling prices.
    - AUTOMATICALLY creates Supplier Purchase Order using original supplier quotation rates (Rule 6, 7).
    - Changing customer selling price NEVER affects supplier purchase rate.
    - Transitions Customer Request status to 'PO Created'.
    """
    cq = db.query(CustomerQuotation).filter(CustomerQuotation.id == obj_in.quotation_id).first()
    if not cq:
        raise ValueError(f"Customer Quotation with ID {obj_in.quotation_id} not found.")

    if cq.status != "Accepted":
        raise ValueError(f"Customer PO can only be created from an accepted quotation. Current status: '{cq.status}'.")

    cr = cq.customer_request
    if not cr:
        raise ValueError("Customer Quotation has no associated Customer Request.")

    # 1. Create Customer Order
    order_no = generate_co_code(db)
    co = CustomerOrder(
        order_no=order_no,
        customer_request_id=cr.id,
        quotation_id=cq.id,
        customer_po_number=obj_in.customer_po_number,
        po_date=obj_in.po_date,
        delivery_date=obj_in.delivery_date,
        status="Open",
    )
    db.add(co)
    db.flush()

    # Determine order items
    order_items_data = []
    if obj_in.items and len(obj_in.items) > 0:
        for it in obj_in.items:
            qty = round_decimal(it.quantity, 2)
            price = round_decimal(it.selling_price, 2)
            lt = round_decimal(qty * price, 2)
            item_record = CustomerOrderItem(
                order_id=co.id,
                item_id=it.item_id,
                quantity=qty,
                selling_price=price,
                line_total=lt,
            )
            db.add(item_record)
            order_items_data.append((it.item_id, qty))
    else:
        for q_item in cq.items:
            qty = round_decimal(q_item.quantity, 2)
            price = round_decimal(q_item.customer_price, 2)
            lt = round_decimal(qty * price, 2)
            item_record = CustomerOrderItem(
                order_id=co.id,
                item_id=q_item.item_id,
                quantity=qty,
                selling_price=price,
                line_total=lt,
            )
            db.add(item_record)
            order_items_data.append((q_item.item_id, qty))

    db.flush()

    # 2. Lookup original supplier rates from winning vendor quotation
    qc = cq.comparison
    pr_id = qc.purchase_request_id if qc else None
    vq = db.query(VendorQuotation).filter(
        VendorQuotation.purchase_request_id == pr_id,
        VendorQuotation.supplier_id == cq.supplier_id
    ).first() if pr_id else None

    sup_rates_map = {}
    if vq and vq.items:
        for vq_item in vq.items:
            if not vq_item.not_quoted and vq_item.rate > 0:
                sup_rates_map[vq_item.item_id] = round_decimal(vq_item.rate, 2)

    # Fallback to cq.items supplier_rate if vendor quote item not found directly
    for q_item in cq.items:
        if q_item.item_id not in sup_rates_map:
            sup_rates_map[q_item.item_id] = round_decimal(q_item.supplier_rate, 2)

    # 3. AUTO CREATE SUPPLIER PURCHASE ORDER
    po_code = generate_po_code(db)
    po = PurchaseOrder(
        po_no=po_code,
        customer_order_id=co.id,
        supplier_id=cq.supplier_id,
        quotation_id=cq.id,
        delivery_date=co.delivery_date,
        status="Draft",
        subtotal=Decimal("0.00"),
        tax=Decimal("0.00"),
        grand_total=Decimal("0.00"),
    )
    db.add(po)
    db.flush()

    po_subtotal = Decimal("0.00")
    for item_id, qty in order_items_data:
        purchase_rate = sup_rates_map.get(item_id, Decimal("0.00"))
        line_tot = round_decimal(qty * purchase_rate, 2)
        po_subtotal += line_tot

        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            item_id=item_id,
            quantity=qty,
            purchase_rate=purchase_rate,
            line_total=line_tot,
        )
        db.add(po_item)

    po_tax = round_decimal(po_subtotal * Decimal("0.18"), 2)
    po.subtotal = round_decimal(po_subtotal, 2)
    po.tax = po_tax
    po.grand_total = round_decimal(po_subtotal + po_tax, 2)

    # 4. Status Update: Customer Request overall stage becomes 'PO Created'
    cr.status = "PO Created"

    db.commit()
    db.refresh(co)
    return co


def get_customer_order_by_id(db: Session, order_id: int) -> Optional[CustomerOrder]:
    """Retrieve Customer Order by ID."""
    return db.query(CustomerOrder).filter(CustomerOrder.id == order_id).first()


def get_customer_orders(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
) -> Tuple[List[CustomerOrder], int]:
    """Retrieve Customer Orders with optional filters and pagination."""
    query = db.query(CustomerOrder)

    if status and status.lower() != "all":
        query = query.filter(CustomerOrder.status.ilike(status.strip()))

    total = query.count()
    items = query.order_by(CustomerOrder.id.desc()).offset(skip).limit(limit).all()
    return items, total

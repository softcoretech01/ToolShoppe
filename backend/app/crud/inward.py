from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.inward import Inward, InwardItem
from app.models.inventory import StockLedger, StockSummary
from app.models.item import Item
from app.models.customer_request import CustomerRequest
from app.schemas.inward import InwardOut, InwardItemOut


def generate_inward_code(db: Session) -> str:
    """Generate next sequential Inward code (e.g. INW-001)."""
    last = db.query(Inward).order_by(Inward.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"INW-{next_num:03d}"
        if not db.query(Inward).filter(Inward.inward_no == code).first():
            return code
        next_num += 1


def format_inward_out(inward: Inward) -> InwardOut:
    """Convert Inward ORM model to schema with full PO, supplier, date, and accepted/rejected breakdown."""
    grn = inward.grn
    cr = inward.customer_request
    sup = grn.supplier if grn else None
    po = grn.purchase_order if grn else None

    # Map GRN line items to get received_qty and rejected_qty for each item
    grn_item_map = {}
    total_rejected = Decimal("0.00")
    if grn and grn.items:
        for gi in grn.items:
            grn_item_map[gi.item_id] = gi
            total_rejected += (gi.rejected_qty or Decimal("0.00"))

    lines_out = []
    total_qty = Decimal("0.00")
    total_value = Decimal("0.00")

    for line in inward.items:
        line_total = line.accepted_qty * line.rate
        total_qty += line.accepted_qty
        total_value += line_total
        gi = grn_item_map.get(line.item_id)
        lines_out.append(
            InwardItemOut(
                id=line.id,
                inward_id=line.inward_id,
                item_id=line.item_id,
                item_name=line.item.name if line.item else None,
                item_code=line.item.item_code if line.item else None,
                received_qty=gi.received_qty if gi else line.accepted_qty,
                accepted_qty=line.accepted_qty,
                rejected_qty=gi.rejected_qty if gi else Decimal("0.00"),
                rate=line.rate,
                line_total=line_total,
            )
        )

    return InwardOut(
        id=inward.id,
        inward_no=inward.inward_no,
        grn_id=inward.grn_id,
        grn_no=grn.grn_no if grn else None,
        po_id=grn.purchase_order_id if grn else None,
        po_no=po.po_no if po else None,
        supplier_id=grn.supplier_id if grn else None,
        supplier_name=sup.name if sup else None,
        customer_request_id=inward.customer_request_id,
        customer_request_no=cr.request_no if cr else None,
        received_date=str(grn.received_date) if (grn and grn.received_date) else None,
        status=inward.status,
        added_at=inward.added_at,
        created_at=inward.created_at,
        total_qty=total_qty,
        total_accepted_qty=total_qty,
        total_rejected_qty=total_rejected,
        total_value=total_value,
        items=lines_out,
    )


def get_inward_by_id(db: Session, inward_id: int) -> Optional[Inward]:
    """Retrieve Inward by ID."""
    return db.query(Inward).filter(Inward.id == inward_id).first()


def get_inwards(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_request_id: Optional[int] = None,
) -> Tuple[List[Inward], int]:
    """Retrieve Inward records with optional filters and pagination."""
    query = db.query(Inward)

    if status and status.lower() != "all":
        query = query.filter(Inward.status.ilike(status.strip()))
    if customer_request_id:
        query = query.filter(Inward.customer_request_id == customer_request_id)

    total = query.count()
    items = query.order_by(Inward.id.desc()).offset(skip).limit(limit).all()
    return items, total


def add_inward_to_inventory(db: Session, inward_id: int) -> Inward:
    """
    Add Inward to Inventory:
    - Verifies inward exists and has not already been added.
    - Creates StockLedger entry (movement_type='IN', reference_type='GRN').
    - Updates/creates StockSummary scoped to customer_request_id and item_id.
    - Updates Item.last_purchase_rate to the received inward rate.
    - Marks Inward status as 'Added' and sets added_at.
    - Updates CustomerRequest.status to 'Stock In'.
    """
    inward = get_inward_by_id(db, inward_id)
    if not inward:
        raise ValueError(f"Inward with ID {inward_id} not found.")

    if inward.status == "Added":
        raise ValueError(f"Inward {inward.inward_no} has already been added to inventory.")

    for line in inward.items:
        if line.accepted_qty <= Decimal("0.00"):
            continue

        # 1. Stock Ledger
        ledger = StockLedger(
            customer_request_id=inward.customer_request_id,
            item_id=line.item_id,
            movement_type="IN",
            quantity=line.accepted_qty,
            rate=line.rate,
            reference_type="GRN",
            reference_id=inward.grn_id,
        )
        db.add(ledger)

        # 2. Stock Summary
        summary = (
            db.query(StockSummary)
            .filter(
                StockSummary.customer_request_id == inward.customer_request_id,
                StockSummary.item_id == line.item_id,
            )
            .first()
        )
        if not summary:
            summary = StockSummary(
                customer_request_id=inward.customer_request_id,
                item_id=line.item_id,
                qty_in=Decimal("0.00"),
                qty_out=Decimal("0.00"),
                on_hand=Decimal("0.00"),
                stock_value=Decimal("0.00"),
            )
            db.add(summary)

        summary.qty_in += line.accepted_qty
        summary.on_hand = summary.qty_in - summary.qty_out
        summary.stock_value += (line.accepted_qty * line.rate)

        # 3. Last Purchase Rate
        item = db.query(Item).filter(Item.id == line.item_id).first()
        if item:
            item.last_purchase_rate = line.rate

    # Update Inward status
    inward.status = "Added"
    inward.added_at = datetime.utcnow()

    # Update Customer Request status to 'Stock In'
    cr = db.query(CustomerRequest).filter(CustomerRequest.id == inward.customer_request_id).first()
    if cr:
        cr.status = "Stock In"

    db.commit()
    db.refresh(inward)
    return inward

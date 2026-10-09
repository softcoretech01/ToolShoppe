from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.grn import GRN, GRNItem
from app.models.inward import Inward, InwardItem
from app.models.purchase_order import PurchaseOrder
from app.schemas.grn import GRNCreate, GRNOut, GRNItemOut


def generate_grn_code(db: Session) -> str:
    """Generate next sequential Goods Receipt Note code (e.g. GRN-001)."""
    last = db.query(GRN).order_by(GRN.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"GRN-{next_num:03d}"
        if not db.query(GRN).filter(GRN.grn_no == code).first():
            return code
        next_num += 1


def format_grn_out(grn: GRN) -> GRNOut:
    """Convert GRN ORM model to schema."""
    lines_out = []
    for line in grn.items:
        lines_out.append(
            GRNItemOut(
                id=line.id,
                grn_id=line.grn_id,
                item_id=line.item_id,
                item_name=line.item.name if line.item else None,
                item_code=line.item.item_code if line.item else None,
                ordered_qty=line.ordered_qty,
                received_qty=line.received_qty,
                accepted_qty=line.accepted_qty,
                rejected_qty=line.rejected_qty,
                purchase_rate=line.purchase_rate,
            )
        )

    po = grn.purchase_order
    cr = grn.customer_request
    sup = grn.supplier
    inw = grn.inward

    return GRNOut(
        id=grn.id,
        grn_no=grn.grn_no,
        purchase_order_id=grn.purchase_order_id,
        purchase_order_no=po.po_no if po else None,
        customer_request_id=grn.customer_request_id,
        customer_request_no=cr.request_no if cr else None,
        supplier_id=grn.supplier_id,
        supplier_name=sup.name if sup else None,
        challan_no=grn.challan_no,
        supplier_invoice_ref=grn.supplier_invoice_ref,
        received_date=grn.received_date,
        received_by=grn.received_by,
        status=grn.status,
        created_at=grn.created_at,
        inward_id=inw.id if inw else None,
        inward_no=inw.inward_no if inw else None,
        items=lines_out,
    )


def get_grn_by_id(db: Session, grn_id: int) -> Optional[GRN]:
    """Retrieve GRN by ID."""
    return db.query(GRN).filter(GRN.id == grn_id).first()


def get_grns(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    purchase_order_id: Optional[int] = None,
    customer_request_id: Optional[int] = None,
) -> Tuple[List[GRN], int]:
    """Retrieve Goods Receipt Notes with optional filters and pagination."""
    query = db.query(GRN)

    if status and status.lower() != "all":
        query = query.filter(GRN.status.ilike(status.strip()))
    if purchase_order_id:
        query = query.filter(GRN.purchase_order_id == purchase_order_id)
    if customer_request_id:
        query = query.filter(GRN.customer_request_id == customer_request_id)

    total = query.count()
    items = query.order_by(GRN.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_grn(db: Session, obj_in: GRNCreate) -> GRN:
    """
    Create a Goods Receipt Note (GRN):
    1. Validate PO status ('Sent' or 'Partially Received').
    2. Validate items against PO and verify:
       - accepted_qty + rejected_qty == received_qty
       - received_qty <= outstanding_qty on PO
    3. Determine PO status ('Partially Received' or 'Received').
    4. Auto-generate Inward document containing ONLY accepted items.
    """
    from app.crud.inward import generate_inward_code

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == obj_in.purchase_order_id).first()
    if not po:
        raise ValueError(f"Purchase Order with ID {obj_in.purchase_order_id} not found.")

    if po.status not in ["Sent", "Partially Received"]:
        raise ValueError(
            f"Cannot create GRN for Purchase Order in '{po.status}' status. "
            f"Purchase Order must be in 'Sent' or 'Partially Received' status."
        )

    # Customer Request reference
    cr_id = None
    if po.customer_order and po.customer_order.customer_request_id:
        cr_id = po.customer_order.customer_request_id
    elif po.quotation and po.quotation.customer_request_id:
        cr_id = po.quotation.customer_request_id

    if not cr_id:
        raise ValueError("Customer Request reference could not be identified for the Purchase Order.")

    po_items_map = {item.item_id: item for item in po.items}

    # Calculate already received quantity per item on this PO
    existing_grns = db.query(GRN).filter(GRN.purchase_order_id == po.id).all()
    existing_grn_ids = [g.id for g in existing_grns]
    already_received_by_item = {}
    if existing_grn_ids:
        existing_items = db.query(GRNItem).filter(GRNItem.grn_id.in_(existing_grn_ids)).all()
        for ei in existing_items:
            already_received_by_item[ei.item_id] = (
                already_received_by_item.get(ei.item_id, Decimal("0.00")) + ei.received_qty
            )

    # Validate input items
    for line in obj_in.items:
        if line.item_id not in po_items_map:
            raise ValueError(f"Item ID {line.item_id} does not belong to Purchase Order {po.po_no}.")

        # Rule 1: Accepted + Rejected == Received
        if (line.accepted_qty + line.rejected_qty) != line.received_qty:
            raise ValueError(
                f"For item ID {line.item_id}, accepted quantity ({line.accepted_qty}) + "
                f"rejected quantity ({line.rejected_qty}) must equal received quantity ({line.received_qty})."
            )

        # Rule 2: Received <= Outstanding
        po_line = po_items_map[line.item_id]
        prev_received = already_received_by_item.get(line.item_id, Decimal("0.00"))
        outstanding_qty = po_line.quantity - prev_received
        if line.received_qty > outstanding_qty:
            raise ValueError(
                f"Received quantity ({line.received_qty}) exceeds outstanding quantity ({outstanding_qty}) "
                f"for item ID {line.item_id}."
            )

    # Create GRN header
    grn_no = generate_grn_code(db)
    grn = GRN(
        grn_no=grn_no,
        purchase_order_id=po.id,
        customer_request_id=cr_id,
        supplier_id=po.supplier_id,
        challan_no=obj_in.challan_no,
        supplier_invoice_ref=obj_in.supplier_invoice_ref,
        received_date=obj_in.received_date,
        received_by=obj_in.received_by,
        status="Received",
    )
    db.add(grn)
    db.flush()

    # Create GRN items
    for line in obj_in.items:
        po_line = po_items_map[line.item_id]
        grn_item = GRNItem(
            grn_id=grn.id,
            item_id=line.item_id,
            ordered_qty=po_line.quantity,
            received_qty=line.received_qty,
            accepted_qty=line.accepted_qty,
            rejected_qty=line.rejected_qty,
            purchase_rate=po_line.purchase_rate,
        )
        db.add(grn_item)
    db.flush()

    # Update PO status
    all_received_map = dict(already_received_by_item)
    for line in obj_in.items:
        all_received_map[line.item_id] = (
            all_received_map.get(line.item_id, Decimal("0.00")) + line.received_qty
        )

    total_ordered = sum(item.quantity for item in po.items)
    total_received = sum(all_received_map.get(item.item_id, Decimal("0.00")) for item in po.items)

    if total_received >= total_ordered:
        po.status = "Received"
    else:
        po.status = "Partially Received"

    # Auto Create Inward document (contains ONLY accepted quantity)
    inward_no = generate_inward_code(db)
    inward = Inward(
        inward_no=inward_no,
        grn_id=grn.id,
        customer_request_id=cr_id,
        status="Pending",
    )
    db.add(inward)
    db.flush()

    for line in obj_in.items:
        if line.accepted_qty > Decimal("0.00"):
            po_line = po_items_map[line.item_id]
            inward_item = InwardItem(
                inward_id=inward.id,
                item_id=line.item_id,
                accepted_qty=line.accepted_qty,
                rate=po_line.purchase_rate,
            )
            db.add(inward_item)
    db.flush()

    db.commit()
    db.refresh(grn)
    return grn

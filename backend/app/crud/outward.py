from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload

from app.models.outward import Outward, OutwardItem
from app.models.customer_order import CustomerOrder
from app.models.inventory import StockLedger, StockSummary
from app.schemas.outward import OutwardCreate, OutwardUpdate, OutwardOut, OutwardItemOut


def generate_outward_code(db: Session) -> str:
    """Generate next sequential Outward code (e.g. OUT-001 or OUT-0001)."""
    last = db.query(Outward).order_by(Outward.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"OUT-{next_num:03d}"
        if not db.query(Outward).filter(Outward.outward_no == code).first():
            return code
        next_num += 1


def format_outward_out(outward: Outward) -> OutwardOut:
    """Convert Outward ORM model to schema."""
    lines_out = []
    for line in outward.items:
        item_unit = line.unit if getattr(line, "unit", None) else (line.item.unit if line.item else "Nos")
        avail_qty = getattr(line, "available_qty", Decimal("0.00"))
        lines_out.append(
            OutwardItemOut(
                id=line.id,
                outward_id=line.outward_id,
                item_id=line.item_id,
                item_name=line.item.name if line.item else None,
                item_code=line.item.item_code if line.item else None,
                ordered_qty=line.ordered_qty,
                available_qty=avail_qty,
                dispatched_qty=line.dispatched_qty,
                dispatch_qty=line.dispatched_qty,
                unit=item_unit,
                unit_price=line.unit_price,
                rate=line.unit_price,
                line_total=line.line_total,
            )
        )

    so = outward.customer_order
    cr = outward.customer_request
    cust = outward.customer

    return OutwardOut(
        id=outward.id,
        outward_no=outward.outward_no,
        customer_order_id=outward.customer_order_id,
        customer_order_no=so.order_no if so else None,
        customer_request_id=outward.customer_request_id,
        customer_request_no=cr.request_no if cr else None,
        customer_id=outward.customer_id,
        customer_name=cust.name if cust else None,
        dc_no=outward.dc_no,
        dc_number=outward.dc_no,
        dispatch_date=outward.dispatch_date,
        dispatch_mode=outward.dispatch_mode,
        vehicle_no=outward.vehicle_no,
        vehicle_or_courier=outward.vehicle_no,
        remarks=outward.remarks,
        status=outward.status,
        total_value=outward.total_value,
        created_at=outward.created_at,
        items=lines_out,
    )


def get_outward_by_id(db: Session, outward_id: int) -> Optional[Outward]:
    """Retrieve Outward by ID."""
    return db.query(Outward).filter(Outward.id == outward_id).first()


def get_outwards(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_order_id: Optional[int] = None,
    customer_request_id: Optional[int] = None,
) -> Tuple[List[Outward], int]:
    """Retrieve Outward records with optional filters and pagination."""
    query = (
        db.query(Outward)
        .options(
            joinedload(Outward.items).joinedload(OutwardItem.item),
            joinedload(Outward.customer_order),
            joinedload(Outward.customer_request),
            joinedload(Outward.customer),
        )
    )

    if status and status.lower() != "all":
        query = query.filter(Outward.status.ilike(status.strip()))
    if customer_order_id:
        query = query.filter(Outward.customer_order_id == customer_order_id)
    if customer_request_id:
        query = query.filter(Outward.customer_request_id == customer_request_id)

    total = query.count()
    items = query.order_by(Outward.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_outward(db: Session, obj_in: OutwardCreate, user_id: Optional[int] = None) -> Outward:
    """
    Create an Outward Delivery Challan:
    1. Validate Customer Order exists (Rule 1).
    2. Validate Customer Order is in dispatchable status ('Open' or 'Partially Dispatched').
    3. Validate items belong to the order (Rule 3).
    4. Validate positive dispatch quantity (Rule 4).
    5. Validate inventory is posted and dispatch <= available on-hand stock (Rule 2, 5, 7).
    6. Validate dispatch <= pending order quantity (Rule 6).
    7. If status is 'Draft', save without stock deduction.
       If status is 'Dispatched', record StockLedger OUT entries, deduct stock, and update status.
    """
    so = db.query(CustomerOrder).filter(CustomerOrder.id == obj_in.customer_order_id).first()
    if not so:
        raise ValueError(f"Customer Order with ID {obj_in.customer_order_id} not found.")

    if so.status not in ["Open", "Partially Dispatched"]:
        raise ValueError(
            f"Cannot dispatch against Customer Order in '{so.status}' status. "
            f"Order must be in 'Open' or 'Partially Dispatched' status."
        )

    cr_id = so.customer_request_id
    cust_id = (
        so.customer_request.customer_id if so.customer_request else
        (so.quotation.customer_id if so.quotation else None)
    )

    if not cust_id:
        raise ValueError("Customer reference could not be determined for the Customer Order.")

    so_items_map = {item.item_id: item for item in so.items}

    # Query already posted dispatched quantities on this Customer Order
    existing_outs = (
        db.query(Outward)
        .filter(Outward.customer_order_id == so.id, Outward.status != "Draft")
        .all()
    )
    existing_out_ids = [o.id for o in existing_outs]
    already_dispatched_map = {}
    if existing_out_ids:
        existing_items = db.query(OutwardItem).filter(OutwardItem.outward_id.in_(existing_out_ids)).all()
        for ei in existing_items:
            already_dispatched_map[ei.item_id] = (
                already_dispatched_map.get(ei.item_id, Decimal("0.00")) + ei.dispatched_qty
            )

    is_draft = (obj_in.status or "").strip().lower() == "draft"

    # Pre-fetch on-hand stock for all order items
    summaries = (
        db.query(StockSummary)
        .filter(StockSummary.customer_request_id == cr_id)
        .all()
    )
    stock_map = {s.item_id: s.on_hand for s in summaries}

    # Check Rule 7: Has inventory been posted for this customer request?
    if not is_draft and not summaries:
        raise ValueError("Cannot dispatch this order. Inventory has not been posted for this customer request.")

    # Validate each input line item
    for line in obj_in.items:
        if line.item_id not in so_items_map:
            raise ValueError(f"Item ID {line.item_id} does not belong to Customer Order {so.order_no}.")

        qty = line.dispatched_qty
        if qty is None or qty <= 0:
            raise ValueError(f"Dispatch quantity must be positive for item ID {line.item_id}.")

        # Guard 1: Cannot exceed pending order balance (Rule 6)
        so_line = so_items_map[line.item_id]
        prev_dispatched = already_dispatched_map.get(line.item_id, Decimal("0.00"))
        pending_so_qty = so_line.quantity - prev_dispatched
        if qty > pending_so_qty:
            raise ValueError(
                f"Dispatched quantity ({qty}) exceeds pending customer order quantity "
                f"({pending_so_qty}) for item ID {line.item_id}."
            )

        # Guard 2: Cannot exceed on-hand stock in StockSummary (Rule 2 & 5)
        available_on_hand = stock_map.get(line.item_id, Decimal("0.00"))
        if not is_draft:
            if available_on_hand <= 0:
                raise ValueError(
                    f"Cannot dispatch this order. Inventory has not been posted for item ID {line.item_id}."
                )
            if qty > available_on_hand:
                cr_no = so.customer_request.request_no if so.customer_request else str(cr_id)
                raise ValueError(
                    f"Dispatched quantity ({qty}) exceeds available on-hand stock "
                    f"({available_on_hand}) for item ID {line.item_id} on Customer Request {cr_no}."
                )

    # Create Outward header
    outward_no = generate_outward_code(db)
    dc_val = obj_in.dc_no or obj_in.dc_number
    vehicle_val = obj_in.vehicle_no or obj_in.vehicle_or_courier

    outward = Outward(
        outward_no=outward_no,
        customer_order_id=so.id,
        customer_request_id=cr_id,
        customer_id=cust_id,
        dc_no=dc_val,
        dispatch_date=obj_in.dispatch_date,
        dispatch_mode=obj_in.dispatch_mode,
        vehicle_no=vehicle_val,
        remarks=obj_in.remarks,
        status="Draft" if is_draft else "Dispatched",
        total_value=Decimal("0.00"),
        created_by=user_id,
    )
    db.add(outward)
    db.flush()

    total_outward_value = Decimal("0.00")

    # Create Outward items
    for line in obj_in.items:
        so_line = so_items_map[line.item_id]
        qty = line.dispatched_qty
        line_total = qty * so_line.selling_price
        total_outward_value += line_total
        avail_qty = stock_map.get(line.item_id, Decimal("0.00"))
        unit_val = line.unit or (so_line.item.unit if so_line.item else "Nos")

        outward_item = OutwardItem(
            outward_id=outward.id,
            item_id=line.item_id,
            ordered_qty=so_line.quantity,
            available_qty=avail_qty,
            dispatched_qty=qty,
            unit=unit_val,
            unit_price=so_line.selling_price,
            line_total=line_total,
        )
        db.add(outward_item)

        if not is_draft:
            # 1. Stock Ledger OUT entry
            ledger = StockLedger(
                customer_request_id=cr_id,
                item_id=line.item_id,
                movement_type="OUT",
                quantity=qty,
                rate=so_line.selling_price,
                reference_type="Outward",
                reference_id=outward.id,
            )
            db.add(ledger)

            # 2. Deduct from StockSummary
            summary = (
                db.query(StockSummary)
                .filter(StockSummary.customer_request_id == cr_id, StockSummary.item_id == line.item_id)
                .first()
            )
            if summary:
                summary.qty_out += qty
                summary.on_hand = summary.qty_in - summary.qty_out

    outward.total_value = total_outward_value

    if not is_draft:
        # Update Customer Order and Customer Request status
        all_dispatched_map = dict(already_dispatched_map)
        for line in obj_in.items:
            all_dispatched_map[line.item_id] = (
                all_dispatched_map.get(line.item_id, Decimal("0.00")) + line.dispatched_qty
            )

        total_ordered = sum(item.quantity for item in so.items)
        total_dispatched = sum(all_dispatched_map.get(item.item_id, Decimal("0.00")) for item in so.items)

        if total_dispatched >= total_ordered:
            outward.status = "Dispatched"
            so.status = "Dispatched"
            if so.customer_request:
                so.customer_request.status = "Dispatched"
        else:
            outward.status = "Partially Dispatched"
            so.status = "Partially Dispatched"

    db.commit()
    db.refresh(outward)
    return outward


def update_outward(db: Session, outward_id: int, obj_in: OutwardUpdate) -> Outward:
    """
    Update a Draft Outward document.
    Enforces Rule 10: Posted documents are immutable.
    """
    outward = get_outward_by_id(db, outward_id)
    if not outward:
        raise ValueError(f"Outward document with ID {outward_id} not found.")

    if outward.status != "Draft":
        raise ValueError(
            f"Cannot edit Outward document in '{outward.status}' status. "
            f"Posted documents are immutable. Only Draft documents can be edited."
        )

    if obj_in.dc_no or obj_in.dc_number:
        outward.dc_no = obj_in.dc_no or obj_in.dc_number
    if obj_in.dispatch_date:
        outward.dispatch_date = obj_in.dispatch_date
    if obj_in.dispatch_mode:
        outward.dispatch_mode = obj_in.dispatch_mode
    if obj_in.vehicle_no or obj_in.vehicle_or_courier:
        outward.vehicle_no = obj_in.vehicle_no or obj_in.vehicle_or_courier
    if obj_in.remarks is not None:
        outward.remarks = obj_in.remarks

    if obj_in.items is not None:
        so = outward.customer_order
        so_items_map = {item.item_id: item for item in so.items}
        # Clear existing items
        db.query(OutwardItem).filter(OutwardItem.outward_id == outward.id).delete()
        total_val = Decimal("0.00")
        for line in obj_in.items:
            if line.item_id not in so_items_map:
                raise ValueError(f"Item ID {line.item_id} does not belong to Customer Order {so.order_no}.")
            qty = line.dispatched_qty
            if qty is None or qty <= 0:
                raise ValueError(f"Dispatch quantity must be positive for item ID {line.item_id}.")
            so_line = so_items_map[line.item_id]
            line_total = qty * so_line.selling_price
            total_val += line_total
            unit_val = line.unit or (so_line.item.unit if so_line.item else "Nos")
            db.add(
                OutwardItem(
                    outward_id=outward.id,
                    item_id=line.item_id,
                    ordered_qty=so_line.quantity,
                    available_qty=Decimal("0.00"),
                    dispatched_qty=qty,
                    unit=unit_val,
                    unit_price=so_line.selling_price,
                    line_total=line_total,
                )
            )
        outward.total_value = total_val

    db.commit()
    db.refresh(outward)
    return outward


def post_outward(db: Session, outward_id: int, user_id: Optional[int] = None) -> Outward:
    """
    Post a Draft Outward document:
    1. Validates available inventory and pending order quantity.
    2. Writes Stock Ledger OUT records.
    3. Deducts stock from StockSummary.
    4. Transitions Outward to 'Dispatched' (or 'Partially Dispatched').
    5. Transitions Customer Order and Request statuses.
    """
    outward = get_outward_by_id(db, outward_id)
    if not outward:
        raise ValueError(f"Outward document with ID {outward_id} not found.")

    if outward.status != "Draft":
        raise ValueError(f"Outward document is already in '{outward.status}' status.")

    so = outward.customer_order
    cr_id = outward.customer_request_id
    so_items_map = {item.item_id: item for item in so.items}

    # Query previously posted dispatched quantities
    existing_outs = (
        db.query(Outward)
        .filter(Outward.customer_order_id == so.id, Outward.id != outward.id, Outward.status != "Draft")
        .all()
    )
    already_dispatched_map = {}
    if existing_outs:
        existing_items = db.query(OutwardItem).filter(
            OutwardItem.outward_id.in_([o.id for o in existing_outs])
        ).all()
        for ei in existing_items:
            already_dispatched_map[ei.item_id] = (
                already_dispatched_map.get(ei.item_id, Decimal("0.00")) + ei.dispatched_qty
            )

    # Validate stock on hand
    summaries = (
        db.query(StockSummary)
        .filter(StockSummary.customer_request_id == cr_id)
        .all()
    )
    if not summaries:
        raise ValueError("Cannot dispatch this order. Inventory has not been posted for this customer request.")

    stock_map = {s.item_id: s.on_hand for s in summaries}

    for line in outward.items:
        so_line = so_items_map.get(line.item_id)
        if not so_line:
            raise ValueError(f"Item ID {line.item_id} does not belong to Customer Order {so.order_no}.")

        prev_dispatched = already_dispatched_map.get(line.item_id, Decimal("0.00"))
        pending_so_qty = so_line.quantity - prev_dispatched
        if line.dispatched_qty > pending_so_qty:
            raise ValueError(
                f"Dispatched quantity ({line.dispatched_qty}) exceeds pending customer order quantity "
                f"({pending_so_qty}) for item ID {line.item_id}."
            )

        available_on_hand = stock_map.get(line.item_id, Decimal("0.00"))
        if available_on_hand <= 0:
            raise ValueError(f"Cannot dispatch this order. Inventory has not been posted for item ID {line.item_id}.")
        if line.dispatched_qty > available_on_hand:
            cr_no = so.customer_request.request_no if so.customer_request else str(cr_id)
            raise ValueError(
                f"Dispatched quantity ({line.dispatched_qty}) exceeds available on-hand stock "
                f"({available_on_hand}) for item ID {line.item_id} on Customer Request {cr_no}."
            )

    # Apply stock movements
    for line in outward.items:
        so_line = so_items_map[line.item_id]
        line.available_qty = stock_map.get(line.item_id, Decimal("0.00"))

        # 1. Stock Ledger OUT
        ledger = StockLedger(
            customer_request_id=cr_id,
            item_id=line.item_id,
            movement_type="OUT",
            quantity=line.dispatched_qty,
            rate=so_line.selling_price,
            reference_type="Outward",
            reference_id=outward.id,
        )
        db.add(ledger)

        # 2. Deduct from StockSummary
        summary = (
            db.query(StockSummary)
            .filter(StockSummary.customer_request_id == cr_id, StockSummary.item_id == line.item_id)
            .first()
        )
        if summary:
            summary.qty_out += line.dispatched_qty
            summary.on_hand = summary.qty_in - summary.qty_out

    # Status update
    all_dispatched_map = dict(already_dispatched_map)
    for line in outward.items:
        all_dispatched_map[line.item_id] = (
            all_dispatched_map.get(line.item_id, Decimal("0.00")) + line.dispatched_qty
        )

    total_ordered = sum(item.quantity for item in so.items)
    total_dispatched = sum(all_dispatched_map.get(item.item_id, Decimal("0.00")) for item in so.items)

    if total_dispatched >= total_ordered:
        outward.status = "Dispatched"
        so.status = "Dispatched"
        if so.customer_request:
            so.customer_request.status = "Dispatched"
    else:
        outward.status = "Partially Dispatched"
        so.status = "Partially Dispatched"

    db.commit()
    db.refresh(outward)
    return outward

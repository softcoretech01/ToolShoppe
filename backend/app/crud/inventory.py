from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.inventory import StockLedger, StockSummary
from app.models.item import Item
from app.schemas.inventory import (
    StockLedgerOut, StockSummaryOut, ItemInventoryOut
)


def format_stock_ledger_out(ledger: StockLedger) -> StockLedgerOut:
    """Convert StockLedger ORM model to schema."""
    cr = ledger.customer_request
    it = ledger.item
    return StockLedgerOut(
        id=ledger.id,
        customer_request_id=ledger.customer_request_id,
        customer_request_no=cr.request_no if cr else None,
        item_id=ledger.item_id,
        item_name=it.name if it else None,
        item_code=it.item_code if it else None,
        movement_type=ledger.movement_type,
        quantity=ledger.quantity,
        rate=ledger.rate,
        reference_type=ledger.reference_type,
        reference_id=ledger.reference_id,
        created_at=ledger.created_at,
    )


def format_stock_summary_out(summary: StockSummary) -> StockSummaryOut:
    """Convert StockSummary ORM model to schema."""
    cr = summary.customer_request
    it = summary.item
    return StockSummaryOut(
        id=summary.id,
        customer_request_id=summary.customer_request_id,
        customer_request_no=cr.request_no if cr else None,
        item_id=summary.item_id,
        item_name=it.name if it else None,
        item_code=it.item_code if it else None,
        qty_in=summary.qty_in,
        qty_out=summary.qty_out,
        on_hand=summary.on_hand,
        stock_value=summary.stock_value,
    )


def get_stock_ledger(
    db: Session,
    customer_request_id: Optional[int] = None,
    item_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[StockLedger], int]:
    """Retrieve Stock Ledger records with optional filters."""
    query = db.query(StockLedger)

    if customer_request_id:
        query = query.filter(StockLedger.customer_request_id == customer_request_id)
    if item_id:
        query = query.filter(StockLedger.item_id == item_id)

    total = query.count()
    items = query.order_by(StockLedger.id.desc()).offset(skip).limit(limit).all()
    return items, total


def get_stock_summaries(
    db: Session,
    customer_request_id: Optional[int] = None,
    item_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[StockSummary], int]:
    """Retrieve Stock Summary records with optional filters."""
    query = db.query(StockSummary)

    if customer_request_id:
        query = query.filter(StockSummary.customer_request_id == customer_request_id)
    if item_id:
        query = query.filter(StockSummary.item_id == item_id)

    total = query.count()
    items = query.order_by(StockSummary.id.desc()).offset(skip).limit(limit).all()
    return items, total


def get_item_inventory(db: Session, item_id: int) -> ItemInventoryOut:
    """Retrieve aggregate inventory status, summaries, and ledger for a specific item."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ValueError(f"Item with ID {item_id} not found.")

    summaries = (
        db.query(StockSummary)
        .filter(StockSummary.item_id == item_id)
        .order_by(StockSummary.id.desc())
        .all()
    )
    ledger = (
        db.query(StockLedger)
        .filter(StockLedger.item_id == item_id)
        .order_by(StockLedger.id.desc())
        .all()
    )

    total_on_hand = sum((s.on_hand for s in summaries), Decimal("0.00"))
    total_value = sum((s.stock_value for s in summaries), Decimal("0.00"))

    return ItemInventoryOut(
        item_id=item.id,
        item_name=item.name,
        item_code=item.item_code,
        last_purchase_rate=item.last_purchase_rate or Decimal("0.00"),
        total_on_hand=total_on_hand,
        total_value=total_value,
        summaries=[format_stock_summary_out(s) for s in summaries],
        ledger=[format_stock_ledger_out(entry) for entry in ledger],
    )

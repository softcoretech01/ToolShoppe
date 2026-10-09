from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class StockLedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_request_id: int
    customer_request_no: Optional[str] = None
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    movement_type: str
    quantity: Decimal
    rate: Decimal
    reference_type: str
    reference_id: int
    created_at: datetime


class StockLedgerListOut(BaseModel):
    total: int
    items: List[StockLedgerOut]


class StockSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_request_id: int
    customer_request_no: Optional[str] = None
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    qty_in: Decimal
    qty_out: Decimal
    on_hand: Decimal
    stock_value: Decimal


class StockSummaryListOut(BaseModel):
    total: int
    items: List[StockSummaryOut]


class ItemInventoryOut(BaseModel):
    item_id: int
    item_name: str
    item_code: Optional[str] = None
    last_purchase_rate: Decimal
    total_on_hand: Decimal
    total_value: Decimal
    summaries: List[StockSummaryOut] = []
    ledger: List[StockLedgerOut] = []

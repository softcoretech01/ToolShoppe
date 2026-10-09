from datetime import date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# --- Sales Report ---
class SalesReportRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    invoice_no: str
    invoice_date: str
    customer_name: str
    item_code: str
    item_name: str
    quantity: Decimal
    unit: str
    rate: Decimal
    sales_value: Decimal
    tax_percent: Decimal
    tax_amount: Decimal
    grand_total: Decimal


class SalesReportOut(BaseModel):
    total_records: int
    total_sales_value: Decimal
    total_tax: Decimal
    total_grand_total: Decimal
    rows: List[SalesReportRow]


# --- Purchase Report ---
class PurchaseReportRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    internal_invoice_no: str
    supplier_invoice_no: str
    supplier_invoice_date: str
    supplier_name: str
    grn_no: str
    item_code: str
    item_name: str
    quantity: Decimal
    unit: str
    rate: Decimal
    purchase_value: Decimal
    tax_percent: Decimal
    tax_amount: Decimal
    grand_total: Decimal


class PurchaseReportOut(BaseModel):
    total_records: int
    total_purchase_value: Decimal
    total_tax: Decimal
    total_grand_total: Decimal
    rows: List[PurchaseReportRow]


# --- Inventory Report ---
class StockSummaryRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    item_code: str
    item_name: str
    unit: str
    total_received: Decimal
    total_dispatched: Decimal
    on_hand: Decimal
    last_rate: Decimal
    stock_value: Decimal


class StockLedgerRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    item_code: str
    item_name: str
    request_no: Optional[str] = None
    movement_type: str
    quantity: Decimal
    rate: Decimal
    reference_type: str
    reference_id: Optional[int] = None


class InventoryReportOut(BaseModel):
    total_stock_value: Decimal
    summary: List[StockSummaryRow]
    ledger: List[StockLedgerRow]


# --- Margin Report ---
class PerRequestMarginRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_request_id: int
    request_no: str
    customer_name: str
    purchase_value: Decimal
    sales_value: Decimal
    margin: Decimal
    margin_percent: Decimal
    status: str


class MarginReportOut(BaseModel):
    overall_sales_value: Decimal
    overall_purchase_value: Decimal
    overall_margin: Decimal
    overall_margin_percent: Decimal
    requests: List[PerRequestMarginRow]

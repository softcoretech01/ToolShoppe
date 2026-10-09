from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PurchaseInvoiceItemCreate(BaseModel):
    item_id: Optional[int] = None
    item_name: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    unit: Optional[str] = None
    rate: Optional[Decimal] = None
    tax_percent: Optional[Decimal] = None


class PurchaseInvoiceCreate(BaseModel):
    grn_id: int
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    supplier_invoice_no: str = Field(..., min_length=1)
    supplier_invoice_date: date
    remarks: Optional[str] = None
    items: Optional[List[PurchaseInvoiceItemCreate]] = None


class PurchaseInvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_invoice_id: int
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    quantity: Decimal
    unit: str
    rate: Decimal
    tax_percent: Decimal
    taxable_value: Decimal
    tax_amount: Decimal
    line_total: Decimal


class PurchaseInvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    internal_invoice_no: str
    grn_id: int
    grn_no: Optional[str] = None
    supplier_id: int
    supplier_name: Optional[str] = None
    customer_request_id: int
    customer_request_no: Optional[str] = None
    supplier_invoice_no: str
    supplier_invoice_date: date
    subtotal: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    status: str
    remarks: Optional[str] = None
    created_at: datetime
    items: List[PurchaseInvoiceItemOut] = []


class PurchaseInvoiceListOut(BaseModel):
    total: int
    items: List[PurchaseInvoiceOut]

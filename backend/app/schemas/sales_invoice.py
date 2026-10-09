from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SalesInvoiceItemCreate(BaseModel):
    item_id: Optional[int] = None
    item_name: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    unit: Optional[str] = None
    rate: Optional[Decimal] = None
    tax_percent: Optional[Decimal] = None


class SalesInvoiceCreate(BaseModel):
    outward_id: int
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    payment_terms: Optional[str] = None
    remarks: Optional[str] = None
    items: Optional[List[SalesInvoiceItemCreate]] = None


class SalesInvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sales_invoice_id: int
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


class SalesInvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_no: str
    outward_id: int
    outward_no: Optional[str] = None
    customer_order_id: int
    customer_order_no: Optional[str] = None
    customer_request_id: int
    customer_request_no: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    invoice_date: date
    due_date: date
    payment_terms: str
    subtotal: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    status: str
    remarks: Optional[str] = None
    created_at: datetime
    items: List[SalesInvoiceItemOut] = []


class SalesInvoicePreviewOut(BaseModel):
    outward_id: int
    outward_no: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    invoice_date: date
    due_date: date
    payment_terms: str
    subtotal: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    items: List[SalesInvoiceItemOut] = []


class SalesInvoiceListOut(BaseModel):
    total: int
    items: List[SalesInvoiceOut]

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PurchaseOrderSendRequest(BaseModel):
    recipient: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class PurchaseOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_id: int
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    quantity: Decimal
    purchase_rate: Decimal
    line_total: Decimal


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_no: str
    customer_order_id: int
    customer_order_no: Optional[str] = None
    customer_po_number: Optional[str] = None
    customer_request_id: Optional[int] = None
    customer_request_no: Optional[str] = None
    supplier_id: int
    supplier_name: Optional[str] = None
    supplier_email: Optional[str] = None
    quotation_id: int
    quotation_no: Optional[str] = None
    delivery_date: Optional[date] = None
    status: str
    sent_at: Optional[datetime] = None
    subtotal: Decimal
    tax: Decimal
    grand_total: Decimal
    created_at: datetime
    items: List[PurchaseOrderItemOut] = []


class PurchaseOrderListOut(BaseModel):
    total: int
    items: List[PurchaseOrderOut]

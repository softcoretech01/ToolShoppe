from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CustomerOrderItemCreate(BaseModel):
    item_id: int
    quantity: Decimal = Field(..., gt=0)
    selling_price: Decimal = Field(..., ge=0)


class CustomerOrderCreate(BaseModel):
    quotation_id: int
    customer_po_number: str = Field(..., min_length=1)
    po_date: date
    delivery_date: Optional[date] = None
    items: Optional[List[CustomerOrderItemCreate]] = None


class CustomerOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    quantity: Decimal
    selling_price: Decimal
    line_total: Decimal


class CustomerOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    customer_request_id: int
    customer_request_no: Optional[str] = None
    quotation_id: int
    quotation_no: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_po_number: str
    po_date: date
    delivery_date: Optional[date] = None
    status: str
    created_at: datetime
    items: List[CustomerOrderItemOut] = []
    auto_purchase_order_id: Optional[int] = None
    auto_purchase_order_no: Optional[str] = None


class CustomerOrderListOut(BaseModel):
    total: int
    items: List[CustomerOrderOut]

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GRNItemCreate(BaseModel):
    item_id: int
    received_qty: Decimal = Field(..., ge=0)
    accepted_qty: Decimal = Field(..., ge=0)
    rejected_qty: Decimal = Field(..., ge=0)


class GRNCreate(BaseModel):
    purchase_order_id: int
    challan_no: str = Field(..., min_length=1)
    supplier_invoice_ref: Optional[str] = None
    received_date: date
    received_by: str = Field(..., min_length=1)
    items: List[GRNItemCreate] = Field(..., min_length=1)


class GRNItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grn_id: int
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    ordered_qty: Decimal
    received_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    purchase_rate: Decimal


class GRNOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grn_no: str
    purchase_order_id: int
    purchase_order_no: Optional[str] = None
    customer_request_id: int
    customer_request_no: Optional[str] = None
    supplier_id: int
    supplier_name: Optional[str] = None
    challan_no: str
    supplier_invoice_ref: Optional[str] = None
    received_date: date
    received_by: str
    status: str
    created_at: datetime
    inward_id: Optional[int] = None
    inward_no: Optional[str] = None
    items: List[GRNItemOut] = []


class GRNListOut(BaseModel):
    total: int
    items: List[GRNOut]

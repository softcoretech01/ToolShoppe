from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class CustomerRequestItemBase(BaseModel):
    item_id: Optional[int] = Field(None, description="Foreign key to item master")
    item_name: Optional[str] = Field(None, description="Item name (can be used instead of item_id)")
    description: Optional[str] = Field(None, description="Custom line description or notes")
    quantity: Decimal = Field(..., gt=0, description="Requested quantity (must be > 0)")
    unit: Optional[str] = Field("Nos", min_length=1, max_length=50, description="Unit of measurement")


class CustomerRequestItemCreate(CustomerRequestItemBase):
    pass


class CustomerRequestItemOut(CustomerRequestItemBase):
    id: int
    request_id: int
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerRequestCreate(BaseModel):
    customer_id: Optional[int] = Field(None, description="Foreign key to customer master")
    customer_name: Optional[str] = Field(None, description="Customer name (can be used instead of customer_id)")
    required_date: Optional[date] = Field(None, description="Date by which goods are required by customer")
    customer_reference: Optional[str] = Field(None, max_length=100, description="Customer enquiry or RFQ reference")
    lines: List[CustomerRequestItemCreate] = Field(..., min_length=1, description="List of item lines (minimum 1 required)")


class CustomerRequestUpdate(BaseModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    required_date: Optional[date] = None
    customer_reference: Optional[str] = None
    lines: Optional[List[CustomerRequestItemCreate]] = None


class CustomerRequestOut(BaseModel):
    id: int
    request_no: str
    customer_id: int
    customer_name: Optional[str] = None
    customer_code: Optional[str] = None
    required_date: Optional[date] = None
    customer_reference: Optional[str] = None
    status: str
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    lines: List[CustomerRequestItemOut] = []
    items_count: int = 0
    total_qty: Decimal = Decimal("0.00")

    class Config:
        from_attributes = True

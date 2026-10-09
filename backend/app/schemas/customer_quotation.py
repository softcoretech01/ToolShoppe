from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CustomerQuotationItemBase(BaseModel):
    item_id: int
    customer_price: Decimal = Field(..., ge=0)


class CustomerQuotationItemUpdate(CustomerQuotationItemBase):
    pass


class CustomerQuotationItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_id: int
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    supplier_rate: Decimal
    customer_price: Decimal
    quantity: Decimal
    margin_percent: Decimal
    line_total: Decimal


class CustomerQuotationUpdate(BaseModel):
    valid_till: Optional[date] = None
    items: Optional[List[CustomerQuotationItemUpdate]] = None


class CustomerQuotationSendRequest(BaseModel):
    quotation_id: Optional[int] = None
    recipient: Optional[str] = None
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)


class CustomerQuotationResendRequest(BaseModel):
    recipient: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class CustomerQuotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_no: str
    customer_request_id: int
    customer_request_no: Optional[str] = None
    comparison_id: int
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    supplier_id: int
    supplier_name: Optional[str] = None
    valid_till: date
    subtotal: Decimal
    tax: Decimal
    grand_total: Decimal
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime
    items: List[CustomerQuotationItemOut] = []


class CustomerQuotationListOut(BaseModel):
    total: int
    items: List[CustomerQuotationOut]

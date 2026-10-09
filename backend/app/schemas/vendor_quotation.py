from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class QuotationItemBase(BaseModel):
    item_id: Optional[int] = None
    item_name: Optional[str] = None
    rate: Decimal = Field(default=Decimal("0.00"), ge=0, description="Unit rate quoted by supplier")
    tax_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100, description="GST tax percentage")
    not_quoted: bool = Field(default=False, description="Whether supplier does not quote for this item")


class QuotationItemCreate(QuotationItemBase):
    pass


class QuotationItemOut(QuotationItemBase):
    id: int
    quotation_id: int
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    line_total: Decimal = Decimal("0.00")

    class Config:
        from_attributes = True


class VendorQuotationCreate(BaseModel):
    purchase_request_id: int = Field(..., description="Purchase Request ID")
    supplier_id: Optional[int] = Field(None, description="Supplier ID")
    supplier_name: Optional[str] = Field(None, description="Supplier Name (can be used instead of supplier_id)")
    quote_reference: Optional[str] = Field(None, max_length=100, description="Supplier's quotation reference number")
    quote_date: Optional[date] = Field(None, description="Date on supplier quotation")
    validity: Optional[date] = Field(None, description="Quote expiration date")
    delivery_days: int = Field(default=0, ge=0, description="Delivery timeframe in days")
    payment_terms: Optional[str] = Field(None, max_length=100, description="Offered payment terms")
    freight: Decimal = Field(default=Decimal("0.00"), ge=0, description="Freight charges in INR")
    lines: List[QuotationItemCreate] = Field(..., min_length=1, description="Quoted rates per item line")


class VendorQuotationUpdate(BaseModel):
    quote_reference: Optional[str] = None
    quote_date: Optional[date] = None
    validity: Optional[date] = None
    delivery_days: Optional[int] = Field(None, ge=0)
    payment_terms: Optional[str] = None
    freight: Optional[Decimal] = Field(None, ge=0)
    lines: Optional[List[QuotationItemCreate]] = None


class VendorQuotationOut(BaseModel):
    id: int
    quotation_no: str
    purchase_request_id: int
    supplier_id: int
    supplier_name: Optional[str] = None
    supplier_code: Optional[str] = None
    quote_reference: Optional[str] = None
    quote_date: Optional[date] = None
    validity: Optional[date] = None
    delivery_days: int
    payment_terms: Optional[str] = None
    freight: Decimal
    subtotal: Decimal
    tax: Decimal
    grand_total: Decimal
    status: str
    created_at: Optional[datetime] = None
    lines: List[QuotationItemOut] = []
    is_complete: bool = True

    class Config:
        from_attributes = True

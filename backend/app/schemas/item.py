from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Item or product name")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name (e.g. Mitutoyo, YG-1, Addison)")
    description: Optional[str] = Field(None, description="Detailed specifications or finish")
    category: Optional[str] = Field(None, max_length=100, description="Product category (e.g. Cutting tools, Hand tools, Measuring, Abrasives)")
    unit: str = Field(..., min_length=1, max_length=50, description="Unit of measurement (e.g. Nos, Set, Box, Kg, Mtr, Pkt)")
    hsn_code: Optional[str] = Field(None, max_length=50, description="Harmonized System of Nomenclature code")
    tax_percent: Decimal = Field(
        default=Decimal("18.00"),
        ge=0,
        le=100,
        description="Applicable GST percentage (0 to 100)"
    )
    last_purchase_rate: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Latest recorded purchase rate in INR"
    )


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    brand: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    hsn_code: Optional[str] = Field(None, max_length=50)
    tax_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    last_purchase_rate: Optional[Decimal] = Field(None, ge=0)


class ItemStatusUpdate(BaseModel):
    status: bool = Field(..., description="Active (true) or Inactive (false)")


class ItemOut(ItemBase):
    id: int
    item_code: str
    status: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

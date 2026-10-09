import re
import json
from datetime import datetime
from typing import Optional, Union, List
from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Supplier company name")
    contact_person: Optional[str] = Field(None, max_length=100, description="Primary contact person name")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    gstin: Optional[str] = Field(None, max_length=50, description="GSTIN number")
    email: str = Field(..., description="Sales/Quotation contact email")
    categories: Optional[Union[List[str], str]] = Field(None, description="Supplied product categories")
    address: Optional[str] = Field(None, description="Supplier address")
    lead_time_days: int = Field(default=0, ge=0, description="Typical fulfillment lead time in days (>= 0)")

    @field_validator("categories", mode="before")
    @classmethod
    def serialize_categories(cls, v):
        if isinstance(v, list):
            return json.dumps(v)
        return v


class SupplierCreate(SupplierBase):
    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v_clean = v.strip()
        if not EMAIL_REGEX.match(v_clean):
            raise ValueError(f"'{v}' is not a valid email address.")
        return v_clean.lower()

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError(f"Mobile number must be exactly 10 digits. Provided: '{v}'")
        return digits


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    gstin: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = None
    categories: Optional[Union[List[str], str]] = None
    address: Optional[str] = None
    lead_time_days: Optional[int] = Field(None, ge=0)

    @field_validator("categories", mode="before")
    @classmethod
    def serialize_categories(cls, v):
        if isinstance(v, list):
            return json.dumps(v)
        return v

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v_clean = v.strip()
        if not EMAIL_REGEX.match(v_clean):
            raise ValueError(f"'{v}' is not a valid email address.")
        return v_clean.lower()

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError(f"Mobile number must be exactly 10 digits. Provided: '{v}'")
        return digits


class SupplierStatusUpdate(BaseModel):
    status: bool = Field(..., description="Active (true) or Inactive (false)")


class SupplierOut(SupplierBase):
    id: int
    supplier_code: str
    status: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

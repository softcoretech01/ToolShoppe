import re
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Customer company name")
    contact_person: Optional[str] = Field(None, max_length=100, description="Contact person name")
    email: str = Field(..., description="Primary contact email address")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    gstin: Optional[str] = Field(None, max_length=50, description="GSTIN number (e.g. 33AABCB1234K1Z5)")
    billing_address: Optional[str] = Field(None, description="Registered billing address")
    shipping_address: Optional[str] = Field(None, description="Delivery or shipping address")
    default_markup: Decimal = Field(
        default=Decimal("10.00"),
        ge=0,
        le=100,
        description="Default markup percentage between 0 and 100"
    )
    payment_terms: Optional[str] = Field(None, max_length=100, description="Agreed payment terms")

class CustomerCreate(CustomerBase):
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


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=50)
    gstin: Optional[str] = Field(None, max_length=50)
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    default_markup: Optional[Decimal] = Field(None, ge=0, le=100)
    payment_terms: Optional[str] = Field(None, max_length=100)

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


class CustomerStatusUpdate(BaseModel):
    status: bool = Field(..., description="Active (true) or Inactive (false)")


class CustomerOut(CustomerBase):
    id: int
    customer_code: str
    status: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

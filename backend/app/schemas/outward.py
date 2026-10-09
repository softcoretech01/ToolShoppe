from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class OutwardItemCreate(BaseModel):
    item_id: int
    dispatched_qty: Optional[Decimal] = Field(None, gt=0)
    dispatch_qty: Optional[Decimal] = Field(None, gt=0)
    ordered_qty: Optional[Decimal] = None
    available_qty: Optional[Decimal] = None
    unit: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_qty(cls, data: dict):
        if isinstance(data, dict):
            qty = data.get("dispatched_qty") or data.get("dispatch_qty")
            if qty is not None:
                data["dispatched_qty"] = Decimal(str(qty))
                data["dispatch_qty"] = Decimal(str(qty))
            else:
                raise ValueError("dispatch_qty or dispatched_qty is required and must be > 0.")
        return data


class OutwardCreate(BaseModel):
    customer_order_id: int
    dc_no: Optional[str] = None
    dc_number: Optional[str] = None
    dispatch_date: date
    dispatch_mode: str = Field("Road", min_length=1)
    vehicle_no: Optional[str] = None
    vehicle_or_courier: Optional[str] = None
    remarks: Optional[str] = None
    status: Optional[str] = "Dispatched"
    items: List[OutwardItemCreate] = Field(..., min_length=1)

    @model_validator(mode="before")
    @classmethod
    def check_fields(cls, data: dict):
        if isinstance(data, dict):
            dc = data.get("dc_no") or data.get("dc_number")
            if not dc:
                raise ValueError("dc_no or dc_number is required.")
            data["dc_no"] = str(dc).strip()
            data["dc_number"] = str(dc).strip()

            vehicle = data.get("vehicle_no") or data.get("vehicle_or_courier")
            if vehicle:
                data["vehicle_no"] = str(vehicle).strip()
                data["vehicle_or_courier"] = str(vehicle).strip()
        return data


class OutwardUpdate(BaseModel):
    dc_no: Optional[str] = None
    dc_number: Optional[str] = None
    dispatch_date: Optional[date] = None
    dispatch_mode: Optional[str] = None
    vehicle_no: Optional[str] = None
    vehicle_or_courier: Optional[str] = None
    remarks: Optional[str] = None
    items: Optional[List[OutwardItemCreate]] = None

    @model_validator(mode="before")
    @classmethod
    def check_fields(cls, data: dict):
        if isinstance(data, dict):
            dc = data.get("dc_no") or data.get("dc_number")
            if dc:
                data["dc_no"] = str(dc).strip()
                data["dc_number"] = str(dc).strip()

            vehicle = data.get("vehicle_no") or data.get("vehicle_or_courier")
            if vehicle:
                data["vehicle_no"] = str(vehicle).strip()
                data["vehicle_or_courier"] = str(vehicle).strip()
        return data


class OutwardItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    outward_id: int
    item_id: int
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    ordered_qty: Decimal
    available_qty: Optional[Decimal] = Decimal("0.00")
    dispatched_qty: Decimal
    dispatch_qty: Optional[Decimal] = None
    unit: Optional[str] = "Nos"
    unit_price: Decimal
    rate: Optional[Decimal] = None
    line_total: Decimal

    @model_validator(mode="after")
    def populate_aliases(self):
        if self.dispatch_qty is None:
            self.dispatch_qty = self.dispatched_qty
        if self.rate is None:
            self.rate = self.unit_price
        return self


class OutwardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    outward_no: str
    customer_order_id: int
    customer_order_no: Optional[str] = None
    customer_request_id: int
    customer_request_no: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    dc_no: str
    dc_number: Optional[str] = None
    dispatch_date: date
    dispatch_mode: str
    vehicle_no: Optional[str] = None
    vehicle_or_courier: Optional[str] = None
    remarks: Optional[str] = None
    status: str
    total_value: Decimal
    created_at: datetime
    items: List[OutwardItemOut] = []

    @model_validator(mode="after")
    def populate_aliases(self):
        if self.dc_number is None:
            self.dc_number = self.dc_no
        if self.vehicle_or_courier is None:
            self.vehicle_or_courier = self.vehicle_no
        return self


class OutwardListOut(BaseModel):
    total: int
    items: List[OutwardOut]

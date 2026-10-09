from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ComparisonItemRate(BaseModel):
    item_id: int
    item_name: str
    item_code: str
    quantity: Decimal
    unit: str
    rates: Dict[int, Optional[Decimal]] = {}  # supplier_id -> rate
    lowest_rate: Optional[Decimal] = None
    cheapest_supplier_id: Optional[int] = None


class ComparisonSupplierSummary(BaseModel):
    supplier_id: int
    supplier_name: str
    supplier_code: str
    quotation_id: int
    quotation_no: str
    delivery_days: int
    freight: Decimal
    subtotal: Decimal
    tax: Decimal
    grand_total: Decimal
    is_complete: bool
    status: str


class ComparisonMatrixOut(BaseModel):
    purchase_request_id: int
    pr_no: str
    customer_request_id: int
    customer_request_no: str
    customer_name: str
    status: str
    recommended_supplier_id: Optional[int] = None
    recommended_supplier_name: Optional[str] = None
    approved_supplier_id: Optional[int] = None
    approved_supplier_name: Optional[str] = None
    override_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    suppliers: List[ComparisonSupplierSummary] = []
    items: List[ComparisonItemRate] = []


class ComparisonApproveRequest(BaseModel):
    selected_supplier_id: int = Field(..., description="ID of supplier to select & approve")
    override_reason: Optional[str] = Field(None, description="Mandatory if selecting supplier other than recommended")

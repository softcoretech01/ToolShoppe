from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.customer_request import CustomerRequestItemOut


class PurchaseRequestOut(BaseModel):
    id: int
    pr_no: str
    customer_request_id: int
    customer_request_no: Optional[str] = None
    customer_name: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    items: List[CustomerRequestItemOut] = []
    suppliers_asked_count: int = 0
    quotes_received_count: int = 0
    rfq_supplier_ids: List[int] = []

    class Config:
        from_attributes = True


class RFQSendRequest(BaseModel):
    pr_id: int = Field(..., description="Purchase Request ID")
    supplier_ids: Optional[List[int]] = Field(None, description="List of supplier IDs to dispatch RFQ to")
    supplier_names: Optional[List[str]] = Field(None, description="List of supplier names to dispatch RFQ to")
    subject: str = Field(..., min_length=1, max_length=255, description="Email subject")
    body: str = Field(..., min_length=1, description="Email body content")

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TimelineEvent(BaseModel):
    stage: str
    title: str
    timestamp: datetime
    document_type: str
    document_no: str
    status: str
    notes: Optional[str] = None


class LinkedDocument(BaseModel):
    document_type: str
    document_no: str
    date: Optional[str] = None
    status: str
    id: int


class OrderTrackingOut(BaseModel):
    customer_request_id: int
    request_no: str
    customer_name: str
    current_stage: str
    stage_index: int
    stages_order: List[str] = [
        "Requested", "RFQ Sent", "Quoted", "Approved", "PO Created", "Stock In", "Dispatched", "Invoiced", "Completed"
    ]
    linked_documents: List[LinkedDocument] = []
    timeline: List[TimelineEvent] = []
    details: Dict[str, Any] = {}

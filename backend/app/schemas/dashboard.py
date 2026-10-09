from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class KPICardsOut(BaseModel):
    total_customer_requests: int
    open_orders: int
    rfq_pending: int
    purchase_orders_draft: int
    stock_available: Decimal
    goods_ready_for_dispatch: Decimal
    sales_value: Decimal
    purchase_value: Decimal
    total_margin: Decimal
    margin_percent: Decimal


class NeedsAttentionItem(BaseModel):
    type: str
    title: str
    document_id: int
    document_no: str
    details: str
    stage: str


class WorkflowSummaryOut(BaseModel):
    customer_requests: int
    rfqs: int
    vendor_quotations: int
    comparisons: int
    customer_orders: int
    purchase_orders: int
    grns: int
    inventory_inwards: int
    outwards: int
    sales_invoices: int
    purchase_invoices: int


class MonthlySalesVsPurchase(BaseModel):
    month: str
    sales_value: Decimal
    purchase_value: Decimal
    margin: Decimal


class StageCount(BaseModel):
    stage: str
    count: int


class BestSellingItem(BaseModel):
    item_id: int
    item_code: str
    item_name: str
    quantity_sold: Decimal
    sales_value: Decimal


class MonthlyMargin(BaseModel):
    month: str
    sales_value: Decimal
    purchase_value: Decimal
    margin: Decimal
    margin_percent: Decimal


class DashboardChartsOut(BaseModel):
    sales_vs_purchase: List[MonthlySalesVsPurchase]
    work_waiting_by_stage: List[StageCount]
    best_selling_items: List[BestSellingItem]
    margin_trend: List[MonthlyMargin]


class DashboardOut(BaseModel):
    kpis: KPICardsOut
    needs_attention: List[NeedsAttentionItem]
    workflow_summary: WorkflowSummaryOut
    charts: DashboardChartsOut

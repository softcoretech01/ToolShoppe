from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.customer_request import CustomerRequest
from app.models.purchase_request import PurchaseRequest
from app.models.vendor_quotation import VendorQuotation
from app.models.quotation_comparison import QuotationComparison
from app.models.customer_order import CustomerOrder, CustomerOrderItem
from app.models.purchase_order import PurchaseOrder
from app.models.grn import GRN
from app.models.inward import Inward
from app.models.inventory import StockSummary
from app.models.outward import Outward
from app.models.sales_invoice import SalesInvoice, SalesInvoiceItem
from app.models.purchase_invoice import PurchaseInvoice
from app.models.email_log import EmailLog
from app.models.item import Item
from app.schemas.dashboard import (
    KPICardsOut, NeedsAttentionItem, WorkflowSummaryOut,
    MonthlySalesVsPurchase, StageCount, BestSellingItem,
    MonthlyMargin, DashboardChartsOut, DashboardOut
)


def get_kpi_cards(db: Session) -> KPICardsOut:
    """Calculate real-time business KPI metrics."""
    tot_requests = db.query(CustomerRequest).count()
    open_orders = db.query(CustomerOrder).filter(CustomerOrder.status.in_(["Open", "Partially Dispatched"])).count()
    rfq_pending = db.query(PurchaseRequest).filter(PurchaseRequest.status.in_(["Open", "RFQ Sent"])).count()
    po_draft = db.query(PurchaseOrder).filter(PurchaseOrder.status == "Draft").count()

    stock_avail_raw = db.query(func.sum(StockSummary.on_hand)).filter(StockSummary.on_hand > 0).scalar()
    stock_avail = Decimal(str(stock_avail_raw or "0.00"))

    # Goods ready for dispatch: stock available on orders not fully dispatched
    ready_raw = (
        db.query(func.sum(StockSummary.on_hand))
        .join(CustomerRequest, CustomerRequest.id == StockSummary.customer_request_id)
        .filter(CustomerRequest.status.in_(["Stock In", "Partially Dispatched"]), StockSummary.on_hand > 0)
        .scalar()
    )
    goods_ready = Decimal(str(ready_raw or "0.00"))

    sales_val_raw = db.query(func.sum(SalesInvoice.grand_total)).scalar()
    sales_val = Decimal(str(sales_val_raw or "0.00"))

    pur_val_raw = db.query(func.sum(PurchaseInvoice.grand_total)).scalar()
    pur_val = Decimal(str(pur_val_raw or "0.00"))

    margin = sales_val - pur_val
    margin_pct = (margin / sales_val * Decimal("100.00")).quantize(Decimal("0.01")) if sales_val > 0 else Decimal("0.00")

    return KPICardsOut(
        total_customer_requests=tot_requests,
        open_orders=open_orders,
        rfq_pending=rfq_pending,
        purchase_orders_draft=po_draft,
        stock_available=stock_avail,
        goods_ready_for_dispatch=goods_ready,
        sales_value=sales_val,
        purchase_value=pur_val,
        total_margin=margin,
        margin_percent=margin_pct,
    )


def get_needs_attention(db: Session) -> List[NeedsAttentionItem]:
    """Scan and list operational tasks needing action."""
    items: List[NeedsAttentionItem] = []

    # 1. RFQ waiting for quotation
    rfq_prs = db.query(PurchaseRequest).filter(PurchaseRequest.status == "RFQ Sent").all()
    for pr in rfq_prs:
        items.append(
            NeedsAttentionItem(
                type="RFQ Waiting",
                title=f"Awaiting supplier quotations for PR #{pr.pr_no}",
                document_id=pr.id,
                document_no=pr.pr_no,
                details="RFQs dispatched to suppliers, awaiting formal quote submissions.",
                stage="RFQ Sent",
            )
        )

    # 2. Draft Purchase Orders
    draft_pos = db.query(PurchaseOrder).filter(PurchaseOrder.status == "Draft").all()
    for po in draft_pos:
        items.append(
            NeedsAttentionItem(
                type="Draft PO",
                title=f"Supplier PO #{po.po_no} pending dispatch",
                document_id=po.id,
                document_no=po.po_no,
                details=f"PO value: INR {po.grand_total:,.2f}. Ready to dispatch to supplier.",
                stage="PO Created",
            )
        )

    # 3. GRN waiting for Inward
    unadded_grns = db.query(GRN).outerjoin(Inward, Inward.grn_id == GRN.id).filter(
        (Inward.id == None) | (Inward.status != "Added")
    ).all()
    for grn in unadded_grns:
        items.append(
            NeedsAttentionItem(
                type="GRN Pending Inward",
                title=f"GRN #{grn.grn_no} goods awaiting inventory posting",
                document_id=grn.id,
                document_no=grn.grn_no,
                details=f"Challan: {grn.challan_no}. Accepted stock not yet posted to warehouse.",
                stage="Stock In",
            )
        )

    # 4. Orders ready for dispatch
    ready_orders = (
        db.query(CustomerOrder)
        .filter(CustomerOrder.status.in_(["Open", "Partially Dispatched"]))
        .all()
    )
    for co in ready_orders:
        cr_id = co.customer_request_id
        on_hand_sum = (
            db.query(func.sum(StockSummary.on_hand))
            .filter(StockSummary.customer_request_id == cr_id, StockSummary.on_hand > 0)
            .scalar()
        )
        if on_hand_sum and Decimal(str(on_hand_sum)) > 0:
            items.append(
                NeedsAttentionItem(
                    type="Ready for Dispatch",
                    title=f"Order #{co.order_no} has available stock ready for DC",
                    document_id=co.id,
                    document_no=co.order_no,
                    details=f"{Decimal(str(on_hand_sum))} units available in warehouse for delivery.",
                    stage="Dispatched",
                )
            )

    # 5. Orders pending invoice
    uninvoiced_outs = db.query(Outward).filter(Outward.status.in_(["Dispatched", "Partially Dispatched"])).all()
    for out in uninvoiced_outs:
        items.append(
            NeedsAttentionItem(
                type="Pending Invoice",
                title=f"Delivery Challan #{out.outward_no} pending Sales Invoice",
                document_id=out.id,
                document_no=out.outward_no,
                details=f"Goods dispatched on {out.dispatch_date}. Sales invoice not yet raised.",
                stage="Invoiced",
            )
        )

    return items


def get_workflow_summary(db: Session) -> WorkflowSummaryOut:
    """Real-time document counts for entire ToolShoppe workflow."""
    return WorkflowSummaryOut(
        customer_requests=db.query(CustomerRequest).count(),
        rfqs=db.query(EmailLog).filter(EmailLog.document_type == "RFQ").count(),
        vendor_quotations=db.query(VendorQuotation).count(),
        comparisons=db.query(QuotationComparison).count(),
        customer_orders=db.query(CustomerOrder).count(),
        purchase_orders=db.query(PurchaseOrder).count(),
        grns=db.query(GRN).count(),
        inventory_inwards=db.query(Inward).count(),
        outwards=db.query(Outward).count(),
        sales_invoices=db.query(SalesInvoice).count(),
        purchase_invoices=db.query(PurchaseInvoice).count(),
    )


def get_dashboard_charts(db: Session) -> DashboardChartsOut:
    """Aggregate analytical data for interactive charts."""
    # 1. Sales vs Purchase by Month
    sales = db.query(SalesInvoice).all()
    purchases = db.query(PurchaseInvoice).all()

    month_data: Dict[str, Dict[str, Decimal]] = {}

    for s in sales:
        m = s.invoice_date.strftime("%Y-%m")
        if m not in month_data:
            month_data[m] = {"sales": Decimal("0.00"), "purchase": Decimal("0.00")}
        month_data[m]["sales"] += s.grand_total

    for p in purchases:
        m = p.supplier_invoice_date.strftime("%Y-%m")
        if m not in month_data:
            month_data[m] = {"sales": Decimal("0.00"), "purchase": Decimal("0.00")}
        month_data[m]["purchase"] += p.grand_total

    sorted_months = sorted(month_data.keys())
    # If no monthly data yet, supply current month
    if not sorted_months:
        curr_m = date.today().strftime("%Y-%m")
        sorted_months = [curr_m]
        month_data[curr_m] = {"sales": Decimal("0.00"), "purchase": Decimal("0.00")}

    sales_vs_purchase: List[MonthlySalesVsPurchase] = []
    margin_trend: List[MonthlyMargin] = []

    for m in sorted_months:
        s_val = month_data[m]["sales"]
        p_val = month_data[m]["purchase"]
        m_val = s_val - p_val
        m_pct = (m_val / s_val * Decimal("100.00")).quantize(Decimal("0.01")) if s_val > 0 else Decimal("0.00")

        sales_vs_purchase.append(
            MonthlySalesVsPurchase(
                month=m,
                sales_value=s_val,
                purchase_value=p_val,
                margin=m_val,
            )
        )
        margin_trend.append(
            MonthlyMargin(
                month=m,
                sales_value=s_val,
                purchase_value=p_val,
                margin=m_val,
                margin_percent=m_pct,
            )
        )

    # 2. Work Waiting by Stage
    stages_order = ["Requested", "RFQ Sent", "Quoted", "Approved", "PO Created", "Stock In", "Dispatched", "Invoiced", "Completed"]
    stage_counts: List[StageCount] = []
    for st in stages_order:
        cnt = db.query(CustomerRequest).filter(CustomerRequest.status == st).count()
        stage_counts.append(StageCount(stage=st, count=cnt))

    # 3. Best Selling Items
    best_selling_items: List[BestSellingItem] = []
    items_agg = (
        db.query(
            SalesInvoiceItem.item_id,
            func.sum(SalesInvoiceItem.quantity).label("total_qty"),
            func.sum(SalesInvoiceItem.line_total).label("total_val")
        )
        .group_by(SalesInvoiceItem.item_id)
        .order_by(func.sum(SalesInvoiceItem.quantity).desc())
        .limit(5)
        .all()
    )

    for it_id, t_qty, t_val in items_agg:
        item = db.query(Item).filter(Item.id == it_id).first()
        best_selling_items.append(
            BestSellingItem(
                item_id=it_id,
                item_code=item.item_code if item else f"ITEM-{it_id}",
                item_name=item.name if item else "Unknown Item",
                quantity_sold=Decimal(str(t_qty or "0.00")),
                sales_value=Decimal(str(t_val or "0.00")),
            )
        )

    return DashboardChartsOut(
        sales_vs_purchase=sales_vs_purchase,
        work_waiting_by_stage=stage_counts,
        best_selling_items=best_selling_items,
        margin_trend=margin_trend,
    )


def get_dashboard(db: Session) -> DashboardOut:
    """Retrieve full aggregated dashboard payload."""
    return DashboardOut(
        kpis=get_kpi_cards(db),
        needs_attention=get_needs_attention(db),
        workflow_summary=get_workflow_summary(db),
        charts=get_dashboard_charts(db),
    )

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.models.customer_request import CustomerRequest
from app.models.purchase_request import PurchaseRequest
from app.models.vendor_quotation import VendorQuotation
from app.models.quotation_comparison import QuotationComparison
from app.models.customer_quotation import CustomerQuotation
from app.models.customer_order import CustomerOrder
from app.models.purchase_order import PurchaseOrder
from app.models.grn import GRN
from app.models.inward import Inward
from app.models.outward import Outward
from app.models.sales_invoice import SalesInvoice
from app.models.purchase_invoice import PurchaseInvoice
from app.models.email_log import EmailLog
from app.schemas.tracking import OrderTrackingOut, TimelineEvent, LinkedDocument


STAGES_ORDER = ["Requested", "RFQ Sent", "Quoted", "Approved", "PO Created", "Stock In", "Dispatched", "Invoiced", "Completed"]


def get_order_tracking(db: Session, cr_id: int) -> OrderTrackingOut:
    """
    Generate the complete sourcing order tracking timeline for a Customer Request.
    Aggregates linked PR, RFQ dispatches, Vendor Quotes, Comparison approval,
    Customer Quotation, Customer PO, and Supplier PO into a chronological audit trail.
    """
    cr = db.query(CustomerRequest).filter(CustomerRequest.id == cr_id).first()
    if not cr:
        raise ValueError(f"Customer Request with ID {cr_id} not found.")

    pr = cr.purchase_request
    qc = pr.quotation_comparison if pr else None
    vqs = pr.vendor_quotations if pr else []
    rfqs = db.query(EmailLog).filter(
        EmailLog.document_type == "RFQ",
        EmailLog.document_id == (pr.id if pr else -1)
    ).order_by(EmailLog.sent_at.asc()).all() if pr else []

    timeline: list[TimelineEvent] = []
    linked_docs: list[LinkedDocument] = []

    # 1. Customer Request
    timeline.append(
        TimelineEvent(
            stage="Requested",
            title=f"Customer Enquiry Recorded ({cr.request_no})",
            timestamp=cr.created_at,
            document_type="Customer Request",
            document_no=cr.request_no,
            status=cr.status,
            notes=f"Reference: {cr.customer_reference or 'N/A'}",
        )
    )
    linked_docs.append(
        LinkedDocument(
            document_type="Customer Request",
            document_no=cr.request_no,
            date=cr.created_at.strftime("%Y-%m-%d"),
            status=cr.status,
            id=cr.id,
        )
    )

    # 2. Purchase Request
    if pr:
        timeline.append(
            TimelineEvent(
                stage="Requested",
                title=f"Purchase Request Generated ({pr.pr_no})",
                timestamp=pr.created_at,
                document_type="Purchase Request",
                document_no=pr.pr_no,
                status=pr.status,
                notes="Created automatically from Customer Request",
            )
        )
        linked_docs.append(
            LinkedDocument(
                document_type="Purchase Request",
                document_no=pr.pr_no,
                date=pr.created_at.strftime("%Y-%m-%d"),
                status=pr.status,
                id=pr.id,
            )
        )

    # 3. RFQs
    for log in rfqs:
        timeline.append(
            TimelineEvent(
                stage="RFQ Sent",
                title=f"RFQ Dispatched to {log.recipient}",
                timestamp=log.sent_at,
                document_type="RFQ Email",
                document_no=f"RFQ-{log.id}",
                status="Sent",
                notes=log.subject,
            )
        )

    # 4. Vendor Quotations
    for vq in vqs:
        timeline.append(
            TimelineEvent(
                stage="Quoted" if vq.status != "Received" else "RFQ Sent",
                title=f"Quotation {vq.quotation_no} from {vq.supplier.name if vq.supplier else 'Supplier'}",
                timestamp=vq.created_at,
                document_type="Vendor Quotation",
                document_no=vq.quotation_no,
                status=vq.status,
                notes=f"Grand Total: INR {vq.grand_total:,.2f} · Delivery: {vq.delivery_days} days",
            )
        )
        linked_docs.append(
            LinkedDocument(
                document_type="Vendor Quotation",
                document_no=vq.quotation_no,
                date=vq.created_at.strftime("%Y-%m-%d"),
                status=vq.status,
                id=vq.id,
            )
        )

    # 5. Quotation Comparison / Approval
    if qc:
        linked_docs.append(
            LinkedDocument(
                document_type="Comparison",
                document_no=f"QC-{qc.id}",
                date=qc.created_at.strftime("%Y-%m-%d"),
                status=qc.status,
                id=qc.id,
            )
        )
        if qc.status == "Approved" and qc.approved_at:
            app_sup = qc.approved_supplier.name if qc.approved_supplier else "Selected Supplier"
            timeline.append(
                TimelineEvent(
                    stage="Approved",
                    title=f"Best Quotation Approved ({app_sup})",
                    timestamp=qc.approved_at,
                    document_type="Comparison Approval",
                    document_no=f"QC-{qc.id}",
                    status="Approved",
                    notes=f"Override reason: {qc.override_reason}" if qc.override_reason else "Approved recommended best quotation",
                )
            )

    # 6. Customer Quotation
    cqs = db.query(CustomerQuotation).filter(CustomerQuotation.customer_request_id == cr_id).all()
    for cq in cqs:
        linked_docs.append(
            LinkedDocument(
                document_type="Customer Quotation",
                document_no=cq.quotation_no,
                date=cq.created_at.strftime("%Y-%m-%d"),
                status=cq.status,
                id=cq.id,
            )
        )
        timeline.append(
            TimelineEvent(
                stage="Approved",
                title=f"Customer Quotation Draft Created ({cq.quotation_no})",
                timestamp=cq.created_at,
                document_type="Customer Quotation",
                document_no=cq.quotation_no,
                status="Draft",
                notes=f"Value: INR {cq.grand_total:,.2f} · Valid till: {cq.valid_till}",
            )
        )
        if cq.sent_at:
            timeline.append(
                TimelineEvent(
                    stage="Approved",
                    title=f"Customer Quotation Dispatched ({cq.quotation_no})",
                    timestamp=cq.sent_at,
                    document_type="Customer Quotation",
                    document_no=cq.quotation_no,
                    status="Sent",
                    notes=f"Quotation email sent to {cq.customer.email if cq.customer else 'Customer'}",
                )
            )
        if cq.status in ["Accepted", "Rejected"]:
            timeline.append(
                TimelineEvent(
                    stage="Approved" if cq.status == "Accepted" else "Requested",
                    title=f"Customer Decision: {cq.status} ({cq.quotation_no})",
                    timestamp=cq.sent_at or cq.created_at,
                    document_type="Customer Decision",
                    document_no=cq.quotation_no,
                    status=cq.status,
                    notes=f"Customer has marked quotation as {cq.status}",
                )
            )

    # 7. Customer Order & Auto Supplier PO
    cos = db.query(CustomerOrder).filter(CustomerOrder.customer_request_id == cr_id).all()
    for co in cos:
        linked_docs.append(
            LinkedDocument(
                document_type="Customer Order",
                document_no=co.order_no,
                date=co.created_at.strftime("%Y-%m-%d"),
                status=co.status,
                id=co.id,
            )
        )
        timeline.append(
            TimelineEvent(
                stage="PO Created",
                title=f"Customer PO Confirmed ({co.order_no})",
                timestamp=co.created_at,
                document_type="Customer Order",
                document_no=co.order_no,
                status=co.status,
                notes=f"Client PO Ref: {co.customer_po_number} · PO Date: {co.po_date}",
            )
        )
        for po in co.purchase_orders:
            linked_docs.append(
                LinkedDocument(
                    document_type="Purchase Order",
                    document_no=po.po_no,
                    date=po.created_at.strftime("%Y-%m-%d"),
                    status=po.status,
                    id=po.id,
                )
            )
            timeline.append(
                TimelineEvent(
                    stage="PO Created",
                    title=f"Auto Supplier PO Created ({po.po_no})",
                    timestamp=po.created_at,
                    document_type="Supplier PO",
                    document_no=po.po_no,
                    status="Draft",
                    notes=f"Supplier: {po.supplier.name if po.supplier else 'Supplier'} · Value: INR {po.grand_total:,.2f}",
                )
            )
            if po.sent_at:
                timeline.append(
                    TimelineEvent(
                        stage="PO Created",
                        title=f"Supplier PO Dispatched ({po.po_no})",
                        timestamp=po.sent_at,
                        document_type="Supplier PO",
                        document_no=po.po_no,
                        status="Sent",
                        notes=f"Dispatched to {po.supplier.email if po.supplier else 'Supplier'}",
                    )
                )

    # 8. Goods Receipt Notes (GRN)
    grns = db.query(GRN).filter(GRN.customer_request_id == cr_id).order_by(GRN.id.asc()).all()
    for grn in grns:
        linked_docs.append(
            LinkedDocument(
                document_type="Goods Receipt Note",
                document_no=grn.grn_no,
                date=grn.received_date.strftime("%Y-%m-%d"),
                status=grn.status,
                id=grn.id,
            )
        )
        timeline.append(
            TimelineEvent(
                stage="Stock In" if cr.status == "Stock In" else "PO Created",
                title=f"Goods Receipt Recorded ({grn.grn_no})",
                timestamp=grn.created_at,
                document_type="Goods Receipt Note",
                document_no=grn.grn_no,
                status=grn.status,
                notes=f"Challan: {grn.challan_no} · Received by: {grn.received_by}",
            )
        )

    # 9. Inward & Inventory
    inwards = db.query(Inward).filter(Inward.customer_request_id == cr_id).order_by(Inward.id.asc()).all()
    for inw in inwards:
        linked_docs.append(
            LinkedDocument(
                document_type="Inward",
                document_no=inw.inward_no,
                date=inw.created_at.strftime("%Y-%m-%d"),
                status=inw.status,
                id=inw.id,
            )
        )
        timeline.append(
            TimelineEvent(
                stage="Stock In" if inw.status == "Added" else "PO Created",
                title=f"Inward Created ({inw.inward_no})",
                timestamp=inw.created_at,
                document_type="Inward",
                document_no=inw.inward_no,
                status=inw.status,
                notes=f"Status: {inw.status}",
            )
        )
        if inw.added_at:
            timeline.append(
                TimelineEvent(
                    stage="Stock In",
                    title=f"Stock Inwarded to Inventory ({inw.inward_no})",
                    timestamp=inw.added_at,
                    document_type="Inventory Addition",
                    document_no=inw.inward_no,
                    status="Added",
                    notes="Added to warehouse stock and stock ledger updated",
                )
            )

    # 10. Outward & Dispatch
    outwards = db.query(Outward).filter(Outward.customer_request_id == cr_id).order_by(Outward.id.asc()).all()
    for out in outwards:
        doc_date = out.dispatch_date.strftime("%Y-%m-%d") if out.dispatch_date else out.created_at.strftime("%Y-%m-%d")
        linked_docs.append(
            LinkedDocument(
                document_type="Delivery Challan",
                document_no=out.outward_no,
                date=doc_date,
                status=out.status,
                id=out.id,
            )
        )
        timeline.append(
            TimelineEvent(
                stage="Dispatched" if out.status in ["Dispatched", "Partially Dispatched"] else "Stock In",
                title=f"Goods Dispatched ({out.outward_no})" if out.status != "Draft" else f"Delivery Challan Draft ({out.outward_no})",
                timestamp=out.created_at,
                document_type="Delivery Challan",
                document_no=out.outward_no,
                status=out.status,
                notes=f"DC Ref: {out.dc_no} · Mode: {out.dispatch_mode} · Value: INR {out.total_value:,.2f}",
            )
        )

    # 11. Sales Invoices
    sales_invoices = db.query(SalesInvoice).filter(SalesInvoice.customer_request_id == cr_id).order_by(SalesInvoice.id.asc()).all()
    for si in sales_invoices:
        linked_docs.append(
            LinkedDocument(
                document_type="Sales Invoice",
                document_no=si.invoice_no,
                date=si.invoice_date.strftime("%Y-%m-%d"),
                status=si.status,
                id=si.id,
            )
        )
        timeline.append(
            TimelineEvent(
                stage="Invoiced" if cr.status in ["Invoiced", "Completed"] else "Dispatched",
                title=f"Sales Invoice Raised ({si.invoice_no})",
                timestamp=si.created_at,
                document_type="Sales Invoice",
                document_no=si.invoice_no,
                status=si.status,
                notes=f"Value: INR {si.grand_total:,.2f} · Due: {si.due_date}",
            )
        )

    # 12. Purchase Invoices
    purchase_invoices = db.query(PurchaseInvoice).filter(PurchaseInvoice.customer_request_id == cr_id).order_by(PurchaseInvoice.id.asc()).all()
    for pi in purchase_invoices:
        linked_docs.append(
            LinkedDocument(
                document_type="Purchase Invoice",
                document_no=pi.internal_invoice_no,
                date=pi.supplier_invoice_date.strftime("%Y-%m-%d"),
                status=pi.status,
                id=pi.id,
            )
        )
        timeline.append(
            TimelineEvent(
                stage="Completed" if cr.status == "Completed" else ("Invoiced" if cr.status == "Invoiced" else "Dispatched"),
                title=f"Purchase Invoice Recorded ({pi.internal_invoice_no})",
                timestamp=pi.created_at,
                document_type="Purchase Invoice",
                document_no=pi.internal_invoice_no,
                status=pi.status,
                notes=f"Supplier Bill: {pi.supplier_invoice_no} · Value: INR {pi.grand_total:,.2f}",
            )
        )

    # 13. Order Completed Event
    if cr.status == "Completed":
        last_dt = cr.created_at
        if purchase_invoices:
            last_dt = max(last_dt, max(p.created_at for p in purchase_invoices))
        if sales_invoices:
            last_dt = max(last_dt, max(s.created_at for s in sales_invoices))
        timeline.append(
            TimelineEvent(
                stage="Completed",
                title=f"Customer Order Completed ({cr.request_no})",
                timestamp=last_dt,
                document_type="Customer Request",
                document_no=cr.request_no,
                status="Completed",
                notes="All items dispatched, customer sales invoice and supplier purchase invoice recorded.",
            )
        )

    # Stage computation
    raw_stage = cr.status
    if raw_stage == "Partially Dispatched":
        curr_stage = "Dispatched"
    elif raw_stage == "Partially Received":
        curr_stage = "Stock In"
    elif raw_stage not in STAGES_ORDER:
        curr_stage = "Requested"
    else:
        curr_stage = raw_stage
    stage_idx = STAGES_ORDER.index(curr_stage)

    # Full lifecycle stages order
    visible_stages = list(STAGES_ORDER)

    # Sort timeline chronologically
    timeline.sort(key=lambda ev: ev.timestamp)

    details = {
        "customer": {
            "name": cr.customer.name if cr.customer else "",
            "code": cr.customer.customer_code if cr.customer else "",
            "email": cr.customer.email if cr.customer else "",
        },
        "items_count": len(cr.items) if cr.items else 0,
        "rfq_count": len(rfqs),
        "quotations_count": len(vqs),
        "comparison_status": qc.status if qc else "Not Started",
        "customer_quotations_count": len(cqs),
        "customer_orders_count": len(cos),
        "grn_count": len(grns),
        "inward_count": len(inwards),
        "outward_count": len(outwards),
        "sales_invoices_count": len(sales_invoices),
        "purchase_invoices_count": len(purchase_invoices),
        "sales_value": float(sum((inv.grand_total for inv in sales_invoices), Decimal("0.00"))),
        "purchase_value": float(sum((inv.grand_total for inv in purchase_invoices), Decimal("0.00"))),
        "margin": float(sum((inv.grand_total for inv in sales_invoices), Decimal("0.00")) - sum((inv.grand_total for inv in purchase_invoices), Decimal("0.00"))),
        "margin_percent": float(
            ((sum((inv.grand_total for inv in sales_invoices), Decimal("0.00")) - sum((inv.grand_total for inv in purchase_invoices), Decimal("0.00"))) / sum((inv.grand_total for inv in sales_invoices), Decimal("0.00")) * Decimal("100.00")).quantize(Decimal("0.01"))
            if sum((inv.grand_total for inv in sales_invoices), Decimal("0.00")) > 0 else Decimal("0.00")
        ),
    }

    return OrderTrackingOut(
        customer_request_id=cr.id,
        request_no=cr.request_no,
        customer_name=cr.customer.name if cr.customer else "",
        current_stage=curr_stage,
        stage_index=stage_idx,
        stages_order=visible_stages,
        linked_documents=linked_docs,
        timeline=timeline,
        details=details,
    )

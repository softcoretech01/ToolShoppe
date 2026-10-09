import csv
import io
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.customer_request import CustomerRequest
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.item import Item
from app.models.sales_invoice import SalesInvoice, SalesInvoiceItem
from app.models.purchase_invoice import PurchaseInvoice, PurchaseInvoiceItem
from app.models.inventory import StockSummary, StockLedger
from app.models.request_margin import RequestMargin
from app.schemas.reports import (
    SalesReportRow, SalesReportOut, PurchaseReportRow, PurchaseReportOut,
    StockSummaryRow, StockLedgerRow, InventoryReportOut,
    PerRequestMarginRow, MarginReportOut
)


def get_sales_report(
    db: Session,
    customer_id: Optional[int] = None,
    item_id: Optional[int] = None,
    invoice_no: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> SalesReportOut:
    """Retrieve Sales Report with item-level details and filtering."""
    query = (
        db.query(SalesInvoiceItem, SalesInvoice, Customer, Item)
        .join(SalesInvoice, SalesInvoice.id == SalesInvoiceItem.sales_invoice_id)
        .join(Customer, Customer.id == SalesInvoice.customer_id)
        .join(Item, Item.id == SalesInvoiceItem.item_id)
    )

    if customer_id:
        query = query.filter(SalesInvoice.customer_id == customer_id)
    if item_id:
        query = query.filter(SalesInvoiceItem.item_id == item_id)
    if invoice_no:
        query = query.filter(SalesInvoice.invoice_no.ilike(f"%{invoice_no.strip()}%"))
    if date_from:
        query = query.filter(SalesInvoice.invoice_date >= date_from)
    if date_to:
        query = query.filter(SalesInvoice.invoice_date <= date_to)

    results = query.order_by(SalesInvoice.invoice_date.desc(), SalesInvoice.id.desc()).all()

    rows: List[SalesReportRow] = []
    tot_sales = Decimal("0.00")
    tot_tax = Decimal("0.00")
    tot_grand = Decimal("0.00")

    for s_item, inv, cust, itm in results:
        tot_sales += s_item.taxable_value
        tot_tax += s_item.tax_amount
        tot_grand += s_item.line_total

        rows.append(
            SalesReportRow(
                invoice_no=inv.invoice_no,
                invoice_date=inv.invoice_date.strftime("%Y-%m-%d"),
                customer_name=cust.name,
                item_code=itm.item_code,
                item_name=itm.name,
                quantity=s_item.quantity,
                unit=s_item.unit,
                rate=s_item.rate,
                sales_value=s_item.taxable_value,
                tax_percent=s_item.tax_percent,
                tax_amount=s_item.tax_amount,
                grand_total=s_item.line_total,
            )
        )

    return SalesReportOut(
        total_records=len(rows),
        total_sales_value=tot_sales,
        total_tax=tot_tax,
        total_grand_total=tot_grand,
        rows=rows,
    )


def get_purchase_report(
    db: Session,
    supplier_id: Optional[int] = None,
    item_id: Optional[int] = None,
    invoice_no: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> PurchaseReportOut:
    """Retrieve Purchase Report with accepted item details and filtering."""
    query = (
        db.query(PurchaseInvoiceItem, PurchaseInvoice, Supplier, Item)
        .join(PurchaseInvoice, PurchaseInvoice.id == PurchaseInvoiceItem.purchase_invoice_id)
        .join(Supplier, Supplier.id == PurchaseInvoice.supplier_id)
        .join(Item, Item.id == PurchaseInvoiceItem.item_id)
    )

    if supplier_id:
        query = query.filter(PurchaseInvoice.supplier_id == supplier_id)
    if item_id:
        query = query.filter(PurchaseInvoiceItem.item_id == item_id)
    if invoice_no:
        search_no = f"%{invoice_no.strip()}%"
        query = query.filter(
            (PurchaseInvoice.internal_invoice_no.ilike(search_no)) |
            (PurchaseInvoice.supplier_invoice_no.ilike(search_no))
        )
    if date_from:
        query = query.filter(PurchaseInvoice.supplier_invoice_date >= date_from)
    if date_to:
        query = query.filter(PurchaseInvoice.supplier_invoice_date <= date_to)

    results = query.order_by(PurchaseInvoice.supplier_invoice_date.desc(), PurchaseInvoice.id.desc()).all()

    rows: List[PurchaseReportRow] = []
    tot_pur = Decimal("0.00")
    tot_tax = Decimal("0.00")
    tot_grand = Decimal("0.00")

    for p_item, inv, sup, itm in results:
        tot_pur += p_item.taxable_value
        tot_tax += p_item.tax_amount
        tot_grand += p_item.line_total
        grn_no = inv.grn.grn_no if inv.grn else "N/A"

        rows.append(
            PurchaseReportRow(
                internal_invoice_no=inv.internal_invoice_no,
                supplier_invoice_no=inv.supplier_invoice_no,
                supplier_invoice_date=inv.supplier_invoice_date.strftime("%Y-%m-%d"),
                supplier_name=sup.name,
                grn_no=grn_no,
                item_code=itm.item_code,
                item_name=itm.name,
                quantity=p_item.quantity,
                unit=p_item.unit,
                rate=p_item.rate,
                purchase_value=p_item.taxable_value,
                tax_percent=p_item.tax_percent,
                tax_amount=p_item.tax_amount,
                grand_total=p_item.line_total,
            )
        )

    return PurchaseReportOut(
        total_records=len(rows),
        total_purchase_value=tot_pur,
        total_tax=tot_tax,
        total_grand_total=tot_grand,
        rows=rows,
    )


def get_inventory_report(
    db: Session,
    item_id: Optional[int] = None,
    batch_no: Optional[str] = None,
    customer_request_id: Optional[int] = None,
) -> InventoryReportOut:
    """Retrieve Stock Summary and Stock Ledger reports."""
    # 1. Stock Summary
    sum_query = db.query(StockSummary, Item).join(Item, Item.id == StockSummary.item_id)
    if item_id:
        sum_query = sum_query.filter(StockSummary.item_id == item_id)
    if customer_request_id:
        sum_query = sum_query.filter(StockSummary.customer_request_id == customer_request_id)

    summary_records = sum_query.order_by(Item.name.asc()).all()
    summary_rows: List[StockSummaryRow] = []
    tot_stock_val = Decimal("0.00")

    for summary, itm in summary_records:
        rate = itm.last_purchase_rate or Decimal("0.00")
        val = summary.on_hand * rate
        tot_stock_val += val
        summary_rows.append(
            StockSummaryRow(
                item_id=itm.id,
                item_code=itm.item_code,
                item_name=itm.name,
                unit=itm.unit,
                total_received=summary.qty_in,
                total_dispatched=summary.qty_out,
                on_hand=summary.on_hand,
                last_rate=rate,
                stock_value=val,
            )
        )

    # 2. Stock Ledger
    led_query = (
        db.query(StockLedger, Item, CustomerRequest)
        .join(Item, Item.id == StockLedger.item_id)
        .outerjoin(CustomerRequest, CustomerRequest.id == StockLedger.customer_request_id)
    )
    if item_id:
        led_query = led_query.filter(StockLedger.item_id == item_id)
    if customer_request_id:
        led_query = led_query.filter(StockLedger.customer_request_id == customer_request_id)

    ledger_records = led_query.order_by(StockLedger.created_at.desc()).all()
    ledger_rows: List[StockLedgerRow] = []

    for led, itm, cr in ledger_records:
        ledger_rows.append(
            StockLedgerRow(
                date=led.created_at.strftime("%Y-%m-%d %H:%M"),
                item_code=itm.item_code,
                item_name=itm.name,
                request_no=cr.request_no if cr else None,
                movement_type=led.movement_type,
                quantity=led.quantity,
                rate=led.rate,
                reference_type=led.reference_type,
                reference_id=led.reference_id,
            )
        )

    return InventoryReportOut(
        total_stock_value=tot_stock_val,
        summary=summary_rows,
        ledger=ledger_rows,
    )


def get_margin_report(
    db: Session,
    customer_id: Optional[int] = None,
    customer_request_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> MarginReportOut:
    """
    Calculate Per Request Margin and Overall Profitability:
    Margin = Sales Value - Purchase Value
    Margin % = (Margin / Sales Value) * 100
    Derived strictly from actual Sales Invoices and Purchase Invoices.
    """
    query = db.query(CustomerRequest).join(Customer, Customer.id == CustomerRequest.customer_id)
    if customer_id:
        query = query.filter(CustomerRequest.customer_id == customer_id)
    if customer_request_id:
        query = query.filter(CustomerRequest.id == customer_request_id)
    if date_from:
        query = query.filter(CustomerRequest.created_at >= date_from)
    if date_to:
        query = query.filter(CustomerRequest.created_at <= date_to)

    requests = query.order_by(CustomerRequest.id.desc()).all()

    rows: List[PerRequestMarginRow] = []
    overall_sales = Decimal("0.00")
    overall_pur = Decimal("0.00")

    for cr in requests:
        # Sum sales value from sales invoices
        s_invoices = db.query(SalesInvoice).filter(SalesInvoice.customer_request_id == cr.id).all()
        s_val = sum((inv.grand_total for inv in s_invoices), Decimal("0.00"))

        # Sum purchase value from purchase invoices
        p_invoices = db.query(PurchaseInvoice).filter(PurchaseInvoice.customer_request_id == cr.id).all()
        p_val = sum((inv.grand_total for inv in p_invoices), Decimal("0.00"))

        margin = s_val - p_val
        margin_pct = (margin / s_val * Decimal("100.00")).quantize(Decimal("0.01")) if s_val > 0 else Decimal("0.00")

        overall_sales += s_val
        overall_pur += p_val

        # Cache / update in RequestMargin table
        req_margin = db.query(RequestMargin).filter(RequestMargin.customer_request_id == cr.id).first()
        if not req_margin:
            req_margin = RequestMargin(
                customer_request_id=cr.id,
                purchase_value=p_val,
                sales_value=s_val,
                margin=margin,
                margin_percent=margin_pct,
            )
            db.add(req_margin)
        else:
            req_margin.purchase_value = p_val
            req_margin.sales_value = s_val
            req_margin.margin = margin
            req_margin.margin_percent = margin_pct

        rows.append(
            PerRequestMarginRow(
                customer_request_id=cr.id,
                request_no=cr.request_no,
                customer_name=cr.customer.name if cr.customer else "Unknown",
                purchase_value=p_val,
                sales_value=s_val,
                margin=margin,
                margin_percent=margin_pct,
                status=cr.status,
            )
        )

    db.commit()

    overall_margin = overall_sales - overall_pur
    overall_margin_pct = (
        (overall_margin / overall_sales * Decimal("100.00")).quantize(Decimal("0.01"))
        if overall_sales > 0 else Decimal("0.00")
    )

    return MarginReportOut(
        overall_sales_value=overall_sales,
        overall_purchase_value=overall_pur,
        overall_margin=overall_margin,
        overall_margin_percent=overall_margin_pct,
        requests=rows,
    )


def generate_csv_output(fieldnames: List[str], data_rows: List[dict]) -> str:
    """Generate RFC 4180 compliant CSV text."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in data_rows:
        writer.writerow(row)
    return output.getvalue()

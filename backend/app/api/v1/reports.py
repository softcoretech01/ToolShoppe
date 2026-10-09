"""
Reports API Endpoints
Comprehensive business reports for Sales, Purchase, Inventory, and Margin Analysis with CSV export.
"""
from datetime import date
from typing import Optional, Union
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.response import SuccessResponse
from app.schemas.reports import (
    SalesReportOut, PurchaseReportOut, InventoryReportOut, MarginReportOut
)
from app.crud.customer import get_customer_by_name
from app.crud.item import get_item_by_name
from app.crud.reports import (
    get_sales_report, get_purchase_report, get_inventory_report,
    get_margin_report, generate_csv_output
)

router = APIRouter(prefix="/reports", tags=["5. Reports & Analytics"])
api_alias_router = APIRouter(prefix="/api/reports", tags=["5. Reports & Analytics"])


@router.get(
    "/sales",
    summary="Get Item-Wise Sales Report",
    description="Retrieve comprehensive sales invoicing report with optional filtering and CSV export."
)
@api_alias_router.get(
    "/sales",
    summary="Get Item-Wise Sales Report",
)
def sales_report(
    customer_id: Optional[int] = Query(None, description="Filter by Customer ID"),
    customer_name: Optional[str] = Query(None, description="Filter by Customer Name"),
    item_id: Optional[int] = Query(None, description="Filter by Item ID"),
    item_name: Optional[str] = Query(None, description="Filter by Item Name"),
    invoice_no: Optional[str] = Query(None, description="Filter by Invoice Number"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    export: Optional[str] = Query(None, description="Set to 'csv' to download as CSV file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if customer_id is None and customer_name:
        cust = get_customer_by_name(db, customer_name)
        if cust:
            customer_id = cust.id

    if item_id is None and item_name:
        itm = get_item_by_name(db, item_name)
        if itm:
            item_id = itm.id

    report = get_sales_report(
        db=db,
        customer_id=customer_id,
        item_id=item_id,
        invoice_no=invoice_no,
        date_from=date_from,
        date_to=date_to,
    )

    if export and export.lower() == "csv":
        fieldnames = [
            "invoice_no", "invoice_date", "customer_name", "item_code",
            "item_name", "quantity", "unit", "rate", "sales_value",
            "tax_percent", "tax_amount", "grand_total"
        ]
        data_rows = [row.model_dump() for row in report.rows]
        csv_content = generate_csv_output(fieldnames, data_rows)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sales_report.csv"}
        )

    return SuccessResponse(
        success=True,
        message="Sales report generated successfully.",
        data=report,
    )


@router.get(
    "/purchase",
    summary="Get Item-Wise Purchase Report",
    description="Retrieve comprehensive supplier purchase invoicing report with filtering and CSV export."
)
@api_alias_router.get(
    "/purchase",
    summary="Get Item-Wise Purchase Report",
)
def purchase_report(
    supplier_id: Optional[int] = Query(None, description="Filter by Supplier ID"),
    item_id: Optional[int] = Query(None, description="Filter by Item ID"),
    invoice_no: Optional[str] = Query(None, description="Filter by Invoice Number"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    export: Optional[str] = Query(None, description="Set to 'csv' to download as CSV file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = get_purchase_report(
        db=db,
        supplier_id=supplier_id,
        item_id=item_id,
        invoice_no=invoice_no,
        date_from=date_from,
        date_to=date_to,
    )

    if export and export.lower() == "csv":
        fieldnames = [
            "internal_invoice_no", "supplier_invoice_no", "supplier_invoice_date",
            "supplier_name", "grn_no", "item_code", "item_name", "quantity",
            "unit", "rate", "purchase_value", "tax_percent", "tax_amount", "grand_total"
        ]
        data_rows = [row.model_dump() for row in report.rows]
        csv_content = generate_csv_output(fieldnames, data_rows)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=purchase_report.csv"}
        )

    return SuccessResponse(
        success=True,
        message="Purchase report generated successfully.",
        data=report,
    )


@router.get(
    "/inventory",
    summary="Get Inventory Stock Summary & Ledger Report",
    description="Retrieve stock summary and complete ledger audit trail with CSV export."
)
@api_alias_router.get(
    "/inventory",
    summary="Get Inventory Stock Summary & Ledger Report",
)
def inventory_report(
    item_id: Optional[int] = Query(None, description="Filter by Item ID"),
    batch_no: Optional[str] = Query(None, description="Filter by Batch Number"),
    customer_request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    export: Optional[str] = Query(None, description="Set to 'csv' to download as CSV file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = get_inventory_report(
        db=db,
        item_id=item_id,
        batch_no=batch_no,
        customer_request_id=customer_request_id,
    )

    if export and export.lower() == "csv":
        fieldnames = [
            "item_id", "item_code", "item_name", "unit",
            "total_received", "total_dispatched", "on_hand",
            "last_rate", "stock_value"
        ]
        data_rows = [row.model_dump() for row in report.summary]
        csv_content = generate_csv_output(fieldnames, data_rows)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=inventory_report.csv"}
        )


    return SuccessResponse(
        success=True,
        message="Inventory report generated successfully.",
        data=report,
    )


@router.get(
    "/margin",
    summary="Get Margin & Profitability Analysis Report",
    description=(
        "Calculate true profit and margin percent per customer request derived strictly "
        "from actual sales invoices and supplier purchase invoices."
    )
)
@api_alias_router.get(
    "/margin",
    summary="Get Margin & Profitability Analysis Report",
)
def margin_report(
    customer_id: Optional[int] = Query(None, description="Filter by Customer ID"),
    customer_name: Optional[str] = Query(None, description="Filter by Customer Name"),
    customer_request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    date_from: Optional[date] = Query(None, description="Filter request creation from date"),
    date_to: Optional[date] = Query(None, description="Filter request creation to date"),
    export: Optional[str] = Query(None, description="Set to 'csv' to download as CSV file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if customer_id is None and customer_name:
        cust = get_customer_by_name(db, customer_name)
        if cust:
            customer_id = cust.id

    report = get_margin_report(
        db=db,
        customer_id=customer_id,
        customer_request_id=customer_request_id,
        date_from=date_from,
        date_to=date_to,
    )

    if export and export.lower() == "csv":
        fieldnames = [
            "customer_request_id", "request_no", "customer_name",
            "purchase_value", "sales_value", "margin", "margin_percent", "status"
        ]
        data_rows = [row.model_dump() for row in report.requests]
        csv_content = generate_csv_output(fieldnames, data_rows)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=margin_report.csv"}
        )

    return SuccessResponse(
        success=True,
        message="Margin report generated successfully.",
        data=report,
    )

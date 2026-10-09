from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_

from app.models.purchase_request import PurchaseRequest, RFQSupplier
from app.models.customer_request import CustomerRequest, CustomerRequestItem
from app.models.supplier import Supplier
from app.crud.supplier import get_supplier_by_name
from app.models.email_log import EmailLog
from app.schemas.customer_request import CustomerRequestItemOut
from app.schemas.purchase_request import PurchaseRequestOut, RFQSendRequest
from app.core.email import send_live_email


def format_pr_out(pr: PurchaseRequest) -> PurchaseRequestOut:
    """Helper to convert PurchaseRequest ORM to PurchaseRequestOut schema."""
    items_out = []
    if pr.customer_request and pr.customer_request.items:
        for line in pr.customer_request.items:
            items_out.append(
                CustomerRequestItemOut(
                    id=line.id,
                    request_id=line.request_id,
                    item_id=line.item_id,
                    item_name=line.item.name if line.item else None,
                    item_code=line.item.item_code if line.item else None,
                    description=line.description,
                    quantity=line.quantity,
                    unit=line.unit,
                )
            )

    suppliers_asked = len(pr.rfq_suppliers) if pr.rfq_suppliers else 0
    quotes_received = len(pr.vendor_quotations) if pr.vendor_quotations else 0
    asked_ids = [r.supplier_id for r in pr.rfq_suppliers] if pr.rfq_suppliers else []

    return PurchaseRequestOut(
        id=pr.id,
        pr_no=pr.pr_no,
        customer_request_id=pr.customer_request_id,
        customer_request_no=pr.customer_request.request_no if pr.customer_request else None,
        customer_name=pr.customer_request.customer.name if (pr.customer_request and pr.customer_request.customer) else None,
        status=pr.status,
        created_at=pr.created_at,
        items=items_out,
        suppliers_asked_count=suppliers_asked,
        quotes_received_count=quotes_received,
        rfq_supplier_ids=asked_ids,
    )


def get_purchase_request_by_id(db: Session, pr_id: int) -> Optional[PurchaseRequest]:
    """Retrieve Purchase Request by ID."""
    return (
        db.query(PurchaseRequest)
        .options(
            joinedload(PurchaseRequest.customer_request).joinedload(CustomerRequest.customer),
            joinedload(PurchaseRequest.customer_request).selectinload(CustomerRequest.items).joinedload(CustomerRequestItem.item),
            selectinload(PurchaseRequest.rfq_suppliers),
            selectinload(PurchaseRequest.vendor_quotations),
        )
        .filter(PurchaseRequest.id == pr_id)
        .first()
    )


def get_purchase_request_by_cr_id(db: Session, cr_id: int) -> Optional[PurchaseRequest]:
    """Retrieve Purchase Request by Customer Request ID."""
    return (
        db.query(PurchaseRequest)
        .options(
            joinedload(PurchaseRequest.customer_request).joinedload(CustomerRequest.customer),
            joinedload(PurchaseRequest.customer_request).selectinload(CustomerRequest.items).joinedload(CustomerRequestItem.item),
            selectinload(PurchaseRequest.rfq_suppliers),
            selectinload(PurchaseRequest.vendor_quotations),
        )
        .filter(PurchaseRequest.customer_request_id == cr_id)
        .first()
    )


def get_purchase_requests(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
    eligible_for_quote: Optional[bool] = None,
) -> Tuple[List[PurchaseRequest], int]:
    """Retrieve Purchase Requests with optional search, status filtering, eligibility filtering, and pagination."""
    query = (
        db.query(PurchaseRequest)
        .join(CustomerRequest)
        .options(
            joinedload(PurchaseRequest.customer_request).joinedload(CustomerRequest.customer),
            joinedload(PurchaseRequest.customer_request).selectinload(CustomerRequest.items).joinedload(CustomerRequestItem.item),
            selectinload(PurchaseRequest.rfq_suppliers),
            selectinload(PurchaseRequest.vendor_quotations),
        )
    )

    if eligible_for_quote:
        query = query.filter(PurchaseRequest.status.in_(["RFQ Sent", "Quoted"])).filter(PurchaseRequest.rfq_suppliers.any())
    elif status and status.lower() != "all":
        query = query.filter(PurchaseRequest.status.ilike(status.strip()))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                PurchaseRequest.pr_no.ilike(pattern),
                CustomerRequest.request_no.ilike(pattern),
                CustomerRequest.customer_reference.ilike(pattern),
            )
        )

    total = query.count()
    items = query.order_by(PurchaseRequest.id.desc()).offset(skip).limit(limit).all()
    return items, total


def send_rfq(
    db: Session,
    rfq_data: RFQSendRequest
) -> Tuple[PurchaseRequest, List[EmailLog]]:
    """
    Dispatch RFQ to selected suppliers:
    1. Associates suppliers with the PR.
    2. Dispatches real email via SMTP and records delivery status & sanitized errors.
    3. Logs an email entry for every supplier recipient.
    4. Updates PR status to 'RFQ Sent' and CR status to 'RFQ Sent'.
    """
    pr = get_purchase_request_by_id(db, rfq_data.pr_id)
    if not pr:
        raise ValueError(f"Purchase Request with ID {rfq_data.pr_id} not found.")

    resolved_sup_ids = set(rfq_data.supplier_ids or [])
    if rfq_data.supplier_names:
        for sname in rfq_data.supplier_names:
            sup = get_supplier_by_name(db, sname)
            if sup:
                resolved_sup_ids.add(sup.id)
            else:
                raise ValueError(f"Supplier '{sname}' not found.")

    if not resolved_sup_ids:
        raise ValueError("At least one supplier (by ID or name) must be specified.")

    created_logs = []
    any_dispatched = False

    for sup_id in resolved_sup_ids:
        supplier = db.query(Supplier).filter(Supplier.id == sup_id).first()
        if not supplier:
            continue

        # Check if already linked as asked
        existing_rfq = db.query(RFQSupplier).filter(
            RFQSupplier.purchase_request_id == pr.id,
            RFQSupplier.supplier_id == sup_id
        ).first()

        if not existing_rfq:
            new_rfq = RFQSupplier(purchase_request_id=pr.id, supplier_id=sup_id)
            db.add(new_rfq)

        # Dispatch real email via SMTP
        delivery_res = None
        if supplier.email:
            delivery_res = send_live_email(
                recipients=supplier.email,
                subject=rfq_data.subject,
                body=rfq_data.body,
            )
            if delivery_res.success:
                any_dispatched = True

        # Log email with exact status and error details
        log = EmailLog(
            document_type="RFQ",
            document_id=pr.id,
            recipient=supplier.email or "No Email Configured",
            subject=rfq_data.subject,
            body=rfq_data.body,
            status=delivery_res.status if delivery_res else "Failed",
            error_message=delivery_res.error_message if delivery_res else "Supplier does not have an email address configured",
        )
        db.add(log)
        created_logs.append(log)

    # Update PR status
    if pr.status == "Open":
        pr.status = "RFQ Sent"

    # Update linked CR status
    if pr.customer_request and pr.customer_request.status == "Requested":
        pr.customer_request.status = "RFQ Sent"

    db.commit()
    db.refresh(pr)
    return pr, created_logs

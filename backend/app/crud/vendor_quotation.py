from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.models.vendor_quotation import VendorQuotation, QuotationItem
from app.models.purchase_request import PurchaseRequest
from app.models.customer_request import CustomerRequest, CustomerRequestItem
from app.models.supplier import Supplier
from app.models.item import Item
from app.crud.supplier import get_supplier_by_name
from app.crud.item import get_item_by_name
from app.schemas.vendor_quotation import VendorQuotationCreate, VendorQuotationUpdate, VendorQuotationOut, QuotationItemOut


def generate_vq_code(db: Session) -> str:
    """Generate next sequential Vendor Quotation code (e.g. VQ-001)."""
    last = db.query(VendorQuotation).order_by(VendorQuotation.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"VQ-{next_num:03d}"
        if not db.query(VendorQuotation).filter(VendorQuotation.quotation_no == code).first():
            return code
        next_num += 1


def format_vq_out(vq: VendorQuotation, db: Session) -> VendorQuotationOut:
    """Helper to convert VendorQuotation ORM to VendorQuotationOut schema."""
    lines_out = []
    quoted_item_ids = set()

    for line in vq.items:
        lines_out.append(
            QuotationItemOut(
                id=line.id,
                quotation_id=line.quotation_id,
                item_id=line.item_id,
                item_name=line.item.name if line.item else None,
                item_code=line.item.item_code if line.item else None,
                rate=line.rate,
                tax_percent=line.tax_percent,
                line_total=line.line_total,
                not_quoted=line.not_quoted,
            )
        )
        if not line.not_quoted and line.rate > 0:
            quoted_item_ids.add(line.item_id)

    # Completeness check: covers all required items in the parent Purchase Request
    pr = vq.purchase_request
    is_complete = True
    if pr and pr.customer_request and pr.customer_request.items:
        req_item_ids = {item.item_id for item in pr.customer_request.items}
        is_complete = req_item_ids.issubset(quoted_item_ids)

    return VendorQuotationOut(
        id=vq.id,
        quotation_no=vq.quotation_no,
        purchase_request_id=vq.purchase_request_id,
        supplier_id=vq.supplier_id,
        supplier_name=vq.supplier.name if vq.supplier else None,
        supplier_code=vq.supplier.supplier_code if vq.supplier else None,
        quote_reference=vq.quote_reference,
        quote_date=vq.quote_date,
        validity=vq.validity,
        delivery_days=vq.delivery_days,
        payment_terms=vq.payment_terms,
        freight=vq.freight,
        subtotal=vq.subtotal,
        tax=vq.tax,
        grand_total=vq.grand_total,
        status=vq.status,
        created_at=vq.created_at,
        lines=lines_out,
        is_complete=is_complete,
    )


def get_vendor_quotation_by_id(db: Session, vq_id: int) -> Optional[VendorQuotation]:
    """Retrieve Vendor Quotation by ID with eager loading."""
    return (
        db.query(VendorQuotation)
        .options(
            joinedload(VendorQuotation.supplier),
            joinedload(VendorQuotation.purchase_request).joinedload(PurchaseRequest.customer_request).joinedload(CustomerRequest.items),
            joinedload(VendorQuotation.items).joinedload(QuotationItem.item),
        )
        .filter(VendorQuotation.id == vq_id)
        .first()
    )


def get_vendor_quotations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    pr_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
) -> Tuple[List[VendorQuotation], int]:
    """Retrieve Vendor Quotations with optional filters and pagination."""
    query = (
        db.query(VendorQuotation)
        .join(Supplier)
        .options(
            joinedload(VendorQuotation.supplier),
            joinedload(VendorQuotation.purchase_request),
            joinedload(VendorQuotation.items).joinedload(QuotationItem.item),
        )
    )

    if pr_id:
        query = query.filter(VendorQuotation.purchase_request_id == pr_id)
    if supplier_id:
        query = query.filter(VendorQuotation.supplier_id == supplier_id)
    if status and status.lower() != "all":
        query = query.filter(VendorQuotation.status.ilike(status.strip()))

    total = query.count()
    items = query.order_by(VendorQuotation.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_vendor_quotation(
    db: Session,
    obj_in: VendorQuotationCreate
) -> VendorQuotation:
    """
    Create a new Vendor Quotation:
    1. Enforces single quotation per supplier per PR.
    2. Calculates line totals using quantities from parent PR.
    3. Calculates subtotal, tax, and grand_total.
    """
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == obj_in.purchase_request_id).first()
    if not pr:
        raise ValueError(f"Purchase Request with ID {obj_in.purchase_request_id} does not exist.")

    # 1. PR Eligibility check: Must have sent RFQs
    if pr.status not in ["RFQ Sent", "Quoted"] or not pr.rfq_suppliers:
        raise ValueError(f"Purchase Request {pr.pr_no} has no sent RFQs and is not eligible to receive Vendor Quotations.")

    if obj_in.supplier_id is None and obj_in.supplier_name:
        sup = get_supplier_by_name(db, obj_in.supplier_name)
        if not sup:
            raise ValueError(f"Supplier '{obj_in.supplier_name}' not found.")
        obj_in.supplier_id = sup.id

    if obj_in.supplier_id is None:
        raise ValueError("Either supplier_id or supplier_name must be provided.")

    # 2. Supplier invitation check: Supplier must be among the RFQ recipients for this PR
    invited_supplier_ids = {rfq.supplier_id for rfq in pr.rfq_suppliers}
    if obj_in.supplier_id not in invited_supplier_ids:
        sup_obj = db.query(Supplier).filter(Supplier.id == obj_in.supplier_id).first()
        sup_display = sup_obj.name if sup_obj else f"ID {obj_in.supplier_id}"
        raise ValueError(
            f"Supplier '{sup_display}' was not invited to quote for Purchase Request {pr.pr_no}. "
            f"Only suppliers with a recorded RFQ can submit quotations."
        )

    # Validation: Same supplier cannot quote twice for the same PR
    existing = db.query(VendorQuotation).filter(
        VendorQuotation.purchase_request_id == obj_in.purchase_request_id,
        VendorQuotation.supplier_id == obj_in.supplier_id
    ).first()
    if existing:
        raise ValueError("This supplier has already submitted a quotation for this Purchase Request.")

    # Resolve items in lines
    for line in obj_in.lines:
        if line.item_id is None and line.item_name:
            itm = get_item_by_name(db, line.item_name)
            if not itm:
                raise ValueError(f"Item '{line.item_name}' not found.")
            line.item_id = itm.id
        elif line.item_id is None:
            raise ValueError("Each line must provide either item_id or item_name.")

    # Build map of item_id -> quantity from CustomerRequest items
    qty_map = {}
    if pr.customer_request and pr.customer_request.items:
        for cr_item in pr.customer_request.items:
            qty_map[cr_item.item_id] = cr_item.quantity

    vq_code = generate_vq_code(db)
    subtotal = Decimal("0.00")
    tax = Decimal("0.00")

    vq = VendorQuotation(
        quotation_no=vq_code,
        purchase_request_id=obj_in.purchase_request_id,
        supplier_id=obj_in.supplier_id,
        quote_reference=obj_in.quote_reference,
        quote_date=obj_in.quote_date,
        validity=obj_in.validity,
        delivery_days=obj_in.delivery_days,
        payment_terms=obj_in.payment_terms,
        freight=obj_in.freight,
        subtotal=Decimal("0.00"),
        tax=Decimal("0.00"),
        grand_total=Decimal("0.00"),
        status="Received",
    )
    db.add(vq)
    db.flush()

    for line in obj_in.lines:
        qty = qty_map.get(line.item_id, Decimal("1.00"))
        if line.not_quoted or line.rate <= 0:
            line_total = Decimal("0.00")
        else:
            line_total = round(line.rate * qty, 2)
            subtotal += line_total
            tax += round((line_total * line.tax_percent) / Decimal("100.00"), 2)

        q_item = QuotationItem(
            quotation_id=vq.id,
            item_id=line.item_id,
            rate=line.rate,
            tax_percent=line.tax_percent,
            line_total=line_total,
            not_quoted=line.not_quoted,
        )
        db.add(q_item)

    vq.subtotal = round(subtotal, 2)
    vq.tax = round(tax, 2)
    vq.grand_total = round(subtotal + tax + obj_in.freight, 2)

    db.commit()
    db.refresh(vq)
    return vq


def update_vendor_quotation(
    db: Session,
    vq: VendorQuotation,
    obj_in: VendorQuotationUpdate
) -> VendorQuotation:
    """Update existing Vendor Quotation details and recalculate totals."""
    if obj_in.quote_reference is not None:
        vq.quote_reference = obj_in.quote_reference
    if obj_in.quote_date is not None:
        vq.quote_date = obj_in.quote_date
    if obj_in.validity is not None:
        vq.validity = obj_in.validity
    if obj_in.delivery_days is not None:
        vq.delivery_days = obj_in.delivery_days
    if obj_in.payment_terms is not None:
        vq.payment_terms = obj_in.payment_terms
    if obj_in.freight is not None:
        vq.freight = obj_in.freight

    if obj_in.lines is not None:
        pr = vq.purchase_request
        qty_map = {}
        if pr and pr.customer_request and pr.customer_request.items:
            for cr_item in pr.customer_request.items:
                qty_map[cr_item.item_id] = cr_item.quantity

        db.query(QuotationItem).filter(QuotationItem.quotation_id == vq.id).delete()
        subtotal = Decimal("0.00")
        tax = Decimal("0.00")

        for line in obj_in.lines:
            qty = qty_map.get(line.item_id, Decimal("1.00"))
            if line.not_quoted or line.rate <= 0:
                line_total = Decimal("0.00")
            else:
                line_total = round(line.rate * qty, 2)
                subtotal += line_total
                tax += round((line_total * line.tax_percent) / Decimal("100.00"), 2)

            q_item = QuotationItem(
                quotation_id=vq.id,
                item_id=line.item_id,
                rate=line.rate,
                tax_percent=line.tax_percent,
                line_total=line_total,
                not_quoted=line.not_quoted,
            )
            db.add(q_item)

        vq.subtotal = round(subtotal, 2)
        vq.tax = round(tax, 2)
        vq.grand_total = round(subtotal + tax + vq.freight, 2)

    db.commit()
    db.refresh(vq)
    return vq

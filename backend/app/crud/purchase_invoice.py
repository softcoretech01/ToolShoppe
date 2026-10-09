from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.purchase_invoice import PurchaseInvoice, PurchaseInvoiceItem
from app.models.grn import GRN, GRNItem
from app.models.supplier import Supplier
from app.models.item import Item
from app.crud.supplier import get_supplier_by_name
from app.crud.item import get_item_by_name
from app.schemas.purchase_invoice import (
    PurchaseInvoiceCreate, PurchaseInvoiceOut, PurchaseInvoiceItemOut
)
from app.crud.sales_invoice import check_and_update_customer_request_status


def generate_purchase_invoice_code(db: Session) -> str:
    """Generate next sequential internal Purchase Invoice code (e.g. PI-0001)."""
    last = db.query(PurchaseInvoice).order_by(PurchaseInvoice.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"PI-{next_num:04d}"
        if not db.query(PurchaseInvoice).filter(PurchaseInvoice.internal_invoice_no == code).first():
            return code
        next_num += 1


def format_purchase_invoice_out(inv: PurchaseInvoice) -> PurchaseInvoiceOut:
    """Convert PurchaseInvoice model to Pydantic schema."""
    lines_out = []
    for line in inv.items:
        lines_out.append(
            PurchaseInvoiceItemOut(
                id=line.id,
                purchase_invoice_id=line.purchase_invoice_id,
                item_id=line.item_id,
                item_name=line.item.name if line.item else None,
                item_code=line.item.item_code if line.item else None,
                quantity=line.quantity,
                unit=line.unit,
                rate=line.rate,
                tax_percent=line.tax_percent,
                taxable_value=line.taxable_value,
                tax_amount=line.tax_amount,
                line_total=line.line_total,
            )
        )

    grn = inv.grn
    sup = inv.supplier
    cr = inv.customer_request

    return PurchaseInvoiceOut(
        id=inv.id,
        internal_invoice_no=inv.internal_invoice_no,
        grn_id=inv.grn_id,
        grn_no=grn.grn_no if grn else None,
        supplier_id=inv.supplier_id,
        supplier_name=sup.name if sup else None,
        customer_request_id=inv.customer_request_id,
        customer_request_no=cr.request_no if cr else None,
        supplier_invoice_no=inv.supplier_invoice_no,
        supplier_invoice_date=inv.supplier_invoice_date,
        subtotal=inv.subtotal,
        tax_amount=inv.tax_amount,
        grand_total=inv.grand_total,
        status=inv.status,
        remarks=inv.remarks,
        created_at=inv.created_at,
        items=lines_out,
    )


def get_purchase_invoice_by_id(db: Session, invoice_id: int) -> Optional[PurchaseInvoice]:
    """Retrieve Purchase Invoice by ID."""
    return db.query(PurchaseInvoice).filter(PurchaseInvoice.id == invoice_id).first()


def get_purchase_invoices(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    customer_request_id: Optional[int] = None,
    grn_id: Optional[int] = None,
) -> Tuple[List[PurchaseInvoice], int]:
    """Retrieve Purchase Invoices with filters and pagination."""
    query = db.query(PurchaseInvoice)

    if status and status.lower() != "all":
        query = query.filter(PurchaseInvoice.status.ilike(status.strip()))
    if supplier_id:
        query = query.filter(PurchaseInvoice.supplier_id == supplier_id)
    if customer_request_id:
        query = query.filter(PurchaseInvoice.customer_request_id == customer_request_id)
    if grn_id:
        query = query.filter(PurchaseInvoice.grn_id == grn_id)

    total = query.count()
    items = query.order_by(PurchaseInvoice.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_purchase_invoice(
    db: Session, obj_in: PurchaseInvoiceCreate, user_id: Optional[int] = None
) -> PurchaseInvoice:
    """
    Create a Purchase Invoice from a GRN:
    1. Validate GRN exists.
    2. Check supplier match if supplier_id provided.
    3. Validate GRN has accepted quantities.
    4. Duplicate checks:
       - Selected GRN has not already been invoiced.
       - Supplier invoice reference has not been duplicated for this supplier.
    5. Bill strictly on accepted quantities (exclude rejected quantities).
    6. Update Customer Request status to 'Completed' if all completion rules are met.
    """
    grn = db.query(GRN).filter(GRN.id == obj_in.grn_id).first()
    if not grn:
        raise ValueError(f"GRN with ID {obj_in.grn_id} not found.")

    supplier_id = obj_in.supplier_id
    if not supplier_id and obj_in.supplier_name:
        s_obj = get_supplier_by_name(db, obj_in.supplier_name)
        if s_obj:
            supplier_id = s_obj.id
    if not supplier_id:
        supplier_id = grn.supplier_id

    if obj_in.supplier_id and obj_in.supplier_id != grn.supplier_id:
        raise ValueError(f"Supplier ID {obj_in.supplier_id} does not match GRN supplier ID {grn.supplier_id}.")

    # Duplicate GRN invoicing protection
    existing_pi_for_grn = db.query(PurchaseInvoice).filter(PurchaseInvoice.grn_id == grn.id).first()
    if existing_pi_for_grn:
        raise ValueError("Cannot create purchase invoice. The selected GRN has already been invoiced.")

    # Duplicate supplier invoice number protection
    supp_inv_no = obj_in.supplier_invoice_no.strip()
    existing_sup_ref = (
        db.query(PurchaseInvoice)
        .filter(
            PurchaseInvoice.supplier_id == supplier_id,
            PurchaseInvoice.supplier_invoice_no == supp_inv_no,
        )
        .first()
    )
    if existing_sup_ref:
        raise ValueError("The same supplier invoice reference should not be recorded repeatedly for the same supplier.")

    accepted_grn_items = [item for item in grn.items if item.accepted_qty > 0]
    if not accepted_grn_items:
        raise ValueError("Cannot create purchase invoice. The selected GRN has no accepted quantities.")

    internal_no = generate_purchase_invoice_code(db)

    purchase_inv = PurchaseInvoice(
        internal_invoice_no=internal_no,
        supplier_id=supplier_id,
        grn_id=grn.id,
        customer_request_id=grn.customer_request_id,
        supplier_invoice_no=supp_inv_no,
        supplier_invoice_date=obj_in.supplier_invoice_date,
        subtotal=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        grand_total=Decimal("0.00"),
        status="Recorded",
        remarks=obj_in.remarks,
        created_by=user_id,
    )
    db.add(purchase_inv)
    db.flush()

    grn_items_map = {item.item_id: item for item in grn.items}
    lines_to_process = obj_in.items if (obj_in.items and len(obj_in.items) > 0) else None

    subtotal = Decimal("0.00")
    total_tax = Decimal("0.00")

    if lines_to_process:
        for line in lines_to_process:
            if line.item_id is None and line.item_name:
                itm_obj = get_item_by_name(db, line.item_name)
                if itm_obj:
                    line.item_id = itm_obj.id
            if line.item_id not in grn_items_map:
                raise ValueError(f"Item ID {line.item_id} is not present in GRN {grn.grn_no}.")
            g_item = grn_items_map[line.item_id]
            if line.quantity > g_item.accepted_qty:
                raise ValueError(
                    f"Invoice quantity ({line.quantity}) cannot exceed GRN accepted quantity "
                    f"({g_item.accepted_qty}) for item ID {line.item_id}."
                )

            rate = line.rate if line.rate is not None else g_item.purchase_rate
            tax_pct = line.tax_percent if line.tax_percent is not None else (
                g_item.item.tax_percent if g_item.item else Decimal("18.00")
            )
            taxable = (line.quantity * rate).quantize(Decimal("0.01"))
            tax = (taxable * (tax_pct / Decimal("100.00"))).quantize(Decimal("0.01"))
            line_tot = taxable + tax

            subtotal += taxable
            total_tax += tax

            pi_item = PurchaseInvoiceItem(
                purchase_invoice_id=purchase_inv.id,
                item_id=line.item_id,
                quantity=line.quantity,
                unit=line.unit or (g_item.item.unit if g_item.item else "Nos"),
                rate=rate,
                tax_percent=tax_pct,
                taxable_value=taxable,
                tax_amount=tax,
                line_total=line_tot,
            )
            db.add(pi_item)
    else:
        for g_item in accepted_grn_items:
            qty = g_item.accepted_qty
            rate = g_item.purchase_rate
            tax_pct = g_item.item.tax_percent if g_item.item else Decimal("18.00")
            taxable = (qty * rate).quantize(Decimal("0.01"))
            tax = (taxable * (tax_pct / Decimal("100.00"))).quantize(Decimal("0.01"))
            line_tot = taxable + tax

            subtotal += taxable
            total_tax += tax

            pi_item = PurchaseInvoiceItem(
                purchase_invoice_id=purchase_inv.id,
                item_id=g_item.item_id,
                quantity=qty,
                unit=g_item.item.unit if g_item.item else "Nos",
                rate=rate,
                tax_percent=tax_pct,
                taxable_value=taxable,
                tax_amount=tax,
                line_total=line_tot,
            )
            db.add(pi_item)

    purchase_inv.subtotal = subtotal
    purchase_inv.tax_amount = total_tax
    purchase_inv.grand_total = subtotal + total_tax

    # Update GRN status to 'Invoiced'
    grn.status = "Invoiced"

    # Check and update customer request status to 'Completed' if both invoices exist
    check_and_update_customer_request_status(db, grn.customer_request_id)

    db.commit()
    db.refresh(purchase_inv)
    return purchase_inv

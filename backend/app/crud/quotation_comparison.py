from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.quotation_comparison import QuotationComparison
from app.models.purchase_request import PurchaseRequest
from app.models.vendor_quotation import VendorQuotation, QuotationItem
from app.models.customer_request import CustomerRequest, CustomerRequestItem
from app.models.supplier import Supplier
from app.schemas.quotation_comparison import (
    ComparisonMatrixOut, ComparisonSupplierSummary, ComparisonItemRate
)


def compute_recommended_supplier_id(
    vqs: List[VendorQuotation],
    required_item_ids: set
) -> Optional[int]:
    """
    Recommendation Decision Tree:
    1. Ignore incomplete quotations (must cover every item with rate > 0 and not_quoted == False).
    2. Lowest Grand Total wins.
    3. If total is equal, shorter delivery days wins.
    4. If still equal, earliest quote date wins.
    """
    eligible = []
    for vq in vqs:
        quoted_items = {
            item.item_id for item in vq.items
            if not item.not_quoted and item.rate > 0
        }
        # Check completeness
        if required_item_ids.issubset(quoted_items):
            eligible.append(vq)

    if not eligible:
        return None

    def sort_key(vq: VendorQuotation):
        date_str = vq.quote_date.isoformat() if vq.quote_date else "9999-99-99"
        return (
            vq.grand_total,
            vq.delivery_days,
            date_str,
            vq.id
        )

    sorted_vqs = sorted(eligible, key=sort_key)
    return sorted_vqs[0].supplier_id


def get_or_create_comparison(db: Session, pr_id: int) -> QuotationComparison:
    """Retrieve existing comparison or initialize a new draft record."""
    qc = db.query(QuotationComparison).filter(QuotationComparison.purchase_request_id == pr_id).first()
    if not qc:
        qc = QuotationComparison(
            purchase_request_id=pr_id,
            status="Draft",
        )
        db.add(qc)
        db.commit()
        db.refresh(qc)
    return qc


def build_comparison_matrix(db: Session, pr_id: int) -> ComparisonMatrixOut:
    """Build the complete side-by-side comparison matrix with recommendation analytics."""
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise ValueError(f"Purchase Request with ID {pr_id} not found.")

    vqs = db.query(VendorQuotation).filter(
        VendorQuotation.purchase_request_id == pr_id
    ).order_by(VendorQuotation.id.asc()).all()

    cr = pr.customer_request
    required_item_ids = {item.item_id for item in cr.items} if (cr and cr.items) else set()

    # Calculate recommended supplier
    recommended_sup_id = compute_recommended_supplier_id(vqs, required_item_ids)

    qc = get_or_create_comparison(db, pr_id)
    if qc.status == "Draft" and qc.recommended_supplier_id != recommended_sup_id:
        qc.recommended_supplier_id = recommended_sup_id
        db.commit()
        db.refresh(qc)

    # 1. Supplier Summaries
    suppliers_summary: List[ComparisonSupplierSummary] = []
    for vq in vqs:
        quoted_items = {
            item.item_id for item in vq.items
            if not item.not_quoted and item.rate > 0
        }
        is_complete = required_item_ids.issubset(quoted_items)

        suppliers_summary.append(
            ComparisonSupplierSummary(
                supplier_id=vq.supplier_id,
                supplier_name=vq.supplier.name if vq.supplier else "Unknown",
                supplier_code=vq.supplier.supplier_code if vq.supplier else "",
                quotation_id=vq.id,
                quotation_no=vq.quotation_no,
                delivery_days=vq.delivery_days,
                freight=vq.freight,
                subtotal=vq.subtotal,
                tax=vq.tax,
                grand_total=vq.grand_total,
                is_complete=is_complete,
                status=vq.status,
            )
        )

    # 2. Per-Item Matrix
    items_matrix: List[ComparisonItemRate] = []
    if cr and cr.items:
        for cr_item in cr.items:
            rates_map: Dict[int, Optional[Decimal]] = {}
            lowest_rate: Optional[Decimal] = None
            cheapest_sup_id: Optional[int] = None

            for vq in vqs:
                q_item = next((item for item in vq.items if item.item_id == cr_item.item_id), None)
                if q_item and not q_item.not_quoted and q_item.rate > 0:
                    rates_map[vq.supplier_id] = q_item.rate
                    if lowest_rate is None or q_item.rate < lowest_rate:
                        lowest_rate = q_item.rate
                        cheapest_sup_id = vq.supplier_id
                else:
                    rates_map[vq.supplier_id] = None

            items_matrix.append(
                ComparisonItemRate(
                    item_id=cr_item.item_id,
                    item_name=cr_item.item.name if cr_item.item else "Unknown",
                    item_code=cr_item.item.item_code if cr_item.item else "",
                    quantity=cr_item.quantity,
                    unit=cr_item.unit,
                    rates=rates_map,
                    lowest_rate=lowest_rate,
                    cheapest_supplier_id=cheapest_sup_id,
                )
            )

    rec_sup = db.query(Supplier).filter(Supplier.id == qc.recommended_supplier_id).first() if qc.recommended_supplier_id else None
    app_sup = db.query(Supplier).filter(Supplier.id == qc.approved_supplier_id).first() if qc.approved_supplier_id else None

    return ComparisonMatrixOut(
        purchase_request_id=pr.id,
        pr_no=pr.pr_no,
        customer_request_id=cr.id if cr else 0,
        customer_request_no=cr.request_no if cr else "",
        customer_name=cr.customer.name if (cr and cr.customer) else "",
        status=qc.status,
        recommended_supplier_id=qc.recommended_supplier_id,
        recommended_supplier_name=rec_sup.name if rec_sup else None,
        approved_supplier_id=qc.approved_supplier_id,
        approved_supplier_name=app_sup.name if app_sup else None,
        override_reason=qc.override_reason,
        approved_at=qc.approved_at,
        suppliers=suppliers_summary,
        items=items_matrix,
    )


def approve_comparison(
    db: Session,
    pr_id: int,
    selected_supplier_id: int,
    override_reason: Optional[str] = None
) -> ComparisonMatrixOut:
    """
    Approve Quotation Comparison:
    - Enforces override reason if choosing different supplier than recommendation.
    - Updates QC status to 'Approved'.
    - Marks selected VQ as 'Selected', all others as 'Rejected'.
    - Transitions PR status to 'Quoted'.
    - Transitions CR status to 'Approved' (per Sourcing Business Rule 8).
    """
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise ValueError(f"Purchase Request with ID {pr_id} not found.")

    vqs = db.query(VendorQuotation).filter(VendorQuotation.purchase_request_id == pr_id).all()
    if not vqs:
        raise ValueError("Cannot approve comparison without any submitted vendor quotations.")

    selected_vq = next((v for v in vqs if v.supplier_id == selected_supplier_id), None)
    if not selected_vq:
        raise ValueError(f"Selected supplier (ID {selected_supplier_id}) has not submitted a quotation for this PR.")

    cr = pr.customer_request
    required_item_ids = {item.item_id for item in cr.items} if (cr and cr.items) else set()
    recommended_id = compute_recommended_supplier_id(vqs, required_item_ids)

    # Validate Override Reason
    if recommended_id and selected_supplier_id != recommended_id:
        if not override_reason or not override_reason.strip():
            raise ValueError(
                "An override reason is mandatory when approving a supplier other than the recommended best quotation."
            )

    qc = get_or_create_comparison(db, pr_id)
    qc.recommended_supplier_id = recommended_id
    qc.approved_supplier_id = selected_supplier_id
    qc.override_reason = override_reason.strip() if override_reason else None
    qc.status = "Approved"
    qc.approved_at = datetime.utcnow()

    # Update VQs
    for vq in vqs:
        if vq.supplier_id == selected_supplier_id:
            vq.status = "Selected"
        else:
            vq.status = "Rejected"

    # Update PR status to 'Quoted'
    pr.status = "Quoted"

    # Update CR status to 'Approved' per Sourcing Rule 8
    if cr:
        cr.status = "Approved"

    db.commit()
    db.refresh(qc)

    # Auto create quotation from approved comparison
    try:
        from app.crud.customer_quotation import auto_create_quotation_from_comparison
        auto_create_quotation_from_comparison(db, qc.id)
    except Exception as exc:
        pass

    return build_comparison_matrix(db, pr_id)

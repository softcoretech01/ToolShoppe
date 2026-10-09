from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.models.customer_request import CustomerRequest, CustomerRequestItem
from app.models.customer import Customer
from app.models.item import Item
from app.models.purchase_request import PurchaseRequest
from app.schemas.customer_request import CustomerRequestCreate, CustomerRequestUpdate, CustomerRequestOut, CustomerRequestItemOut


def generate_cr_code(db: Session) -> str:
    """Generate the next sequential Customer Request code (e.g. CR-001)."""
    last = db.query(CustomerRequest).order_by(CustomerRequest.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"CR-{next_num:03d}"
        if not db.query(CustomerRequest).filter(CustomerRequest.request_no == code).first():
            return code
        next_num += 1


def generate_pr_code(db: Session) -> str:
    """Generate the next sequential Purchase Request code (e.g. PR-001)."""
    last = db.query(PurchaseRequest).order_by(PurchaseRequest.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"PR-{next_num:03d}"
        if not db.query(PurchaseRequest).filter(PurchaseRequest.pr_no == code).first():
            return code
        next_num += 1


def format_cr_out(cr: CustomerRequest) -> CustomerRequestOut:
    """Helper to convert CustomerRequest ORM object to CustomerRequestOut schema."""
    lines_out = []
    total_qty = 0
    for line in cr.items:
        lines_out.append(
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
        total_qty += line.quantity

    return CustomerRequestOut(
        id=cr.id,
        request_no=cr.request_no,
        customer_id=cr.customer_id,
        customer_name=cr.customer.name if cr.customer else None,
        customer_code=cr.customer.customer_code if cr.customer else None,
        required_date=cr.required_date,
        customer_reference=cr.customer_reference,
        status=cr.status,
        created_by=cr.created_by,
        created_at=cr.created_at,
        lines=lines_out,
        items_count=len(lines_out),
        total_qty=total_qty,
    )


def get_customer_request_by_id(db: Session, cr_id: int) -> Optional[CustomerRequest]:
    """Retrieve Customer Request by ID."""
    return db.query(CustomerRequest).filter(CustomerRequest.id == cr_id).first()


def get_customer_requests(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[CustomerRequest], int]:
    """Retrieve Customer Requests with optional search, status filtering, and pagination."""
    query = (
        db.query(CustomerRequest)
        .join(Customer)
        .options(
            joinedload(CustomerRequest.customer),
            joinedload(CustomerRequest.items).joinedload(CustomerRequestItem.item),
        )
    )

    if status and status.lower() != "all":
        query = query.filter(CustomerRequest.status.ilike(status.strip()))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                CustomerRequest.request_no.ilike(pattern),
                CustomerRequest.customer_reference.ilike(pattern),
                Customer.name.ilike(pattern),
                Customer.customer_code.ilike(pattern),
            )
        )

    total = query.count()
    items = query.order_by(CustomerRequest.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_customer_request(
    db: Session,
    obj_in: CustomerRequestCreate,
    user_id: Optional[int] = None
) -> CustomerRequest:
    """
    Create a new Customer Request and automatically create matching Purchase Request (PR)
    with identical lines as mandated by the automated sourcing workflow.
    """
    cr_code = generate_cr_code(db)
    cr = CustomerRequest(
        request_no=cr_code,
        customer_id=obj_in.customer_id,
        required_date=obj_in.required_date,
        customer_reference=obj_in.customer_reference,
        status="Requested",
        created_by=user_id,
    )
    db.add(cr)
    db.flush()

    # Add line items
    for line in obj_in.lines:
        cr_item = CustomerRequestItem(
            request_id=cr.id,
            item_id=line.item_id,
            description=line.description,
            quantity=line.quantity,
            unit=line.unit,
        )
        db.add(cr_item)

    # AUTO CREATE PURCHASE REQUEST (PR)
    pr_code = generate_pr_code(db)
    pr = PurchaseRequest(
        pr_no=pr_code,
        customer_request_id=cr.id,
        status="Open",
    )
    db.add(pr)

    db.commit()
    db.refresh(cr)
    return cr


def update_customer_request(
    db: Session,
    cr: CustomerRequest,
    obj_in: CustomerRequestUpdate
) -> CustomerRequest:
    """
    Update Customer Request.
    Allowed only if status is 'Requested' (prior to RFQ send).
    """
    if cr.status != "Requested":
        raise ValueError("Customer Request is locked and cannot be edited after RFQ has been sent.")

    if obj_in.customer_id is not None:
        cr.customer_id = obj_in.customer_id
    if obj_in.required_date is not None:
        cr.required_date = obj_in.required_date
    if obj_in.customer_reference is not None:
        cr.customer_reference = obj_in.customer_reference

    if obj_in.lines is not None:
        # Clear existing lines and replace
        db.query(CustomerRequestItem).filter(CustomerRequestItem.request_id == cr.id).delete()
        for line in obj_in.lines:
            cr_item = CustomerRequestItem(
                request_id=cr.id,
                item_id=line.item_id,
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
            )
            db.add(cr_item)

    db.commit()
    db.refresh(cr)
    return cr

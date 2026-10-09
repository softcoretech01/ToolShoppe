from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


def generate_customer_code(db: Session) -> str:
    """Generate the next unique customer code (e.g. CUS-001)."""
    last = db.query(Customer).order_by(Customer.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"CUS-{next_num:03d}"
        if not db.query(Customer).filter(Customer.customer_code == code).first():
            return code
        next_num += 1


def get_customer_by_id(db: Session, customer_id: int) -> Optional[Customer]:
    """Retrieve customer by primary key."""
    return db.query(Customer).filter(Customer.id == customer_id).first()


def get_customer_by_name(db: Session, name: str) -> Optional[Customer]:
    """
    Retrieve customer by exact/case-insensitive name, customer code, or numeric ID.
    """
    if not name:
        return None
    clean = str(name).strip()
    # 1. Exact case-insensitive name match
    cust = db.query(Customer).filter(Customer.name.ilike(clean)).first()
    if cust:
        return cust
    # 2. Customer code match
    cust = db.query(Customer).filter(Customer.customer_code.ilike(clean)).first()
    if cust:
        return cust
    # 3. Numeric ID fallback
    if clean.isdigit():
        cust = db.query(Customer).filter(Customer.id == int(clean)).first()
        if cust:
            return cust
    # 4. Partial name match fallback
    cust = db.query(Customer).filter(Customer.name.ilike(f"%{clean}%")).first()
    if cust:
        return cust
    return None


def get_customer_by_code(db: Session, code: str) -> Optional[Customer]:
    """Retrieve customer by code."""
    return db.query(Customer).filter(Customer.customer_code == code).first()


def get_customer_by_email(db: Session, email: str) -> Optional[Customer]:
    """Retrieve customer by email address."""
    return db.query(Customer).filter(Customer.email == email).first()


def get_customers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[Customer], int]:
    """
    Retrieve customers with optional search, status filtering, and pagination.
    Returns (items, total_count).
    """
    query = db.query(Customer)

    # Status filter: 'active', 'inactive', or 'all'
    if status is not None:
        status_clean = status.lower().strip()
        if status_clean in ("true", "active", "1"):
            query = query.filter(Customer.status == True)
        elif status_clean in ("false", "inactive", "0"):
            query = query.filter(Customer.status == False)

    # Search filter (name, customer_code, email, phone)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(search_pattern),
                Customer.customer_code.ilike(search_pattern),
                Customer.contact_person.ilike(search_pattern),
                Customer.email.ilike(search_pattern),
                Customer.phone.ilike(search_pattern),
            )
        )

    total = query.count()
    items = query.order_by(Customer.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_customer(db: Session, obj_in: CustomerCreate) -> Customer:
    """Create a new customer with auto-generated code."""
    code = generate_customer_code(db)
    db_obj = Customer(
        customer_code=code,
        name=obj_in.name,
        contact_person=obj_in.contact_person,
        email=obj_in.email,
        phone=obj_in.phone,
        gstin=obj_in.gstin,
        billing_address=obj_in.billing_address,
        shipping_address=obj_in.shipping_address,
        default_markup=obj_in.default_markup,
        payment_terms=obj_in.payment_terms,
        status=True,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_customer(db: Session, db_obj: Customer, obj_in: CustomerUpdate) -> Customer:
    """Update existing customer details."""
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_customer_status(db: Session, db_obj: Customer, status: bool) -> Customer:
    """Activate or deactivate a customer (soft delete)."""
    db_obj.status = status
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_customer(db: Session, db_obj: Customer) -> Customer:
    """Permanently delete a customer record."""
    db.delete(db_obj)
    db.commit()
    return db_obj


from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


def generate_supplier_code(db: Session) -> str:
    """Generate the next unique supplier code (e.g. SUP-001)."""
    last = db.query(Supplier).order_by(Supplier.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"SUP-{next_num:03d}"
        if not db.query(Supplier).filter(Supplier.supplier_code == code).first():
            return code
        next_num += 1


def get_supplier_by_id(db: Session, supplier_id: int) -> Optional[Supplier]:
    """Retrieve supplier by primary key."""
    return db.query(Supplier).filter(Supplier.id == supplier_id).first()


def get_supplier_by_name(db: Session, name: str) -> Optional[Supplier]:
    """
    Retrieve supplier by exact/case-insensitive name, supplier code, or numeric ID.
    """
    if not name:
        return None
    clean = str(name).strip()
    # 1. Exact case-insensitive name match
    sup = db.query(Supplier).filter(Supplier.name.ilike(clean)).first()
    if sup:
        return sup
    # 2. Supplier code match
    sup = db.query(Supplier).filter(Supplier.supplier_code.ilike(clean)).first()
    if sup:
        return sup
    # 3. Numeric ID fallback
    if clean.isdigit():
        sup = db.query(Supplier).filter(Supplier.id == int(clean)).first()
        if sup:
            return sup
    # 4. Partial name match fallback
    sup = db.query(Supplier).filter(Supplier.name.ilike(f"%{clean}%")).first()
    if sup:
        return sup
    return None


def get_supplier_by_code(db: Session, code: str) -> Optional[Supplier]:
    """Retrieve supplier by code."""
    return db.query(Supplier).filter(Supplier.supplier_code == code).first()


def get_supplier_by_email(db: Session, email: str) -> Optional[Supplier]:
    """Retrieve supplier by email address."""
    return db.query(Supplier).filter(Supplier.email == email).first()


def get_suppliers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[Supplier], int]:
    """
    Retrieve suppliers with optional search, status filtering, and pagination.
    Returns (items, total_count).
    """
    query = db.query(Supplier)

    # Status filter: 'active', 'inactive', or 'all'
    if status is not None:
        status_clean = status.lower().strip()
        if status_clean in ("true", "active", "1"):
            query = query.filter(Supplier.status == True)
        elif status_clean in ("false", "inactive", "0"):
            query = query.filter(Supplier.status == False)

    # Search filter (name, supplier_code, email, contact_person, categories, gstin, phone)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Supplier.name.ilike(search_pattern),
                Supplier.supplier_code.ilike(search_pattern),
                Supplier.email.ilike(search_pattern),
                Supplier.contact_person.ilike(search_pattern),
                Supplier.categories.ilike(search_pattern),
                Supplier.gstin.ilike(search_pattern),
                Supplier.phone.ilike(search_pattern),
            )
        )

    total = query.count()
    items = query.order_by(Supplier.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_supplier(db: Session, obj_in: SupplierCreate) -> Supplier:
    """Create a new supplier with auto-generated code."""
    code = generate_supplier_code(db)
    db_obj = Supplier(
        supplier_code=code,
        name=obj_in.name,
        contact_person=obj_in.contact_person,
        phone=obj_in.phone,
        gstin=obj_in.gstin,
        email=obj_in.email,
        categories=obj_in.categories,
        address=obj_in.address,
        lead_time_days=obj_in.lead_time_days,
        status=True,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_supplier(db: Session, db_obj: Supplier, obj_in: SupplierUpdate) -> Supplier:
    """Update existing supplier details."""
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_supplier_status(db: Session, db_obj: Supplier, status: bool) -> Supplier:
    """Activate or deactivate a supplier (soft delete)."""
    db_obj.status = status
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_supplier(db: Session, db_obj: Supplier) -> Supplier:
    """Permanently delete a supplier record."""
    db.delete(db_obj)
    db.commit()
    return db_obj


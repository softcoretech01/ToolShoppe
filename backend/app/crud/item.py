from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate


def generate_item_code(db: Session) -> str:
    """Generate the next unique item code (e.g. ITM-0001)."""
    last = db.query(Item).order_by(Item.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        code = f"ITM-{next_num:04d}"
        if not db.query(Item).filter(Item.item_code == code).first():
            return code
        next_num += 1


def get_item_by_id(db: Session, item_id: int) -> Optional[Item]:
    """Retrieve item by primary key."""
    return db.query(Item).filter(Item.id == item_id).first()


def get_item_by_name(db: Session, name: str) -> Optional[Item]:
    """
    Retrieve item by exact/case-insensitive name, item code, or numeric ID.
    """
    if not name:
        return None
    clean = str(name).strip()
    # 1. Exact case-insensitive name match
    itm = db.query(Item).filter(Item.name.ilike(clean)).first()
    if itm:
        return itm
    # 2. Item code match
    itm = db.query(Item).filter(Item.item_code.ilike(clean)).first()
    if itm:
        return itm
    # 3. Numeric ID fallback
    if clean.isdigit():
        itm = db.query(Item).filter(Item.id == int(clean)).first()
        if itm:
            return itm
    # 4. Partial name match fallback
    itm = db.query(Item).filter(Item.name.ilike(f"%{clean}%")).first()
    if itm:
        return itm
    return None


def get_item_by_code(db: Session, code: str) -> Optional[Item]:
    """Retrieve item by unique item code."""
    return db.query(Item).filter(Item.item_code == code).first()


def get_items(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[Item], int]:
    """
    Retrieve items with optional search, category, status filtering, and pagination.
    Returns (items, total_count).
    """
    query = db.query(Item)

    # Status filter: 'active', 'inactive', or 'all'
    if status is not None:
        status_clean = status.lower().strip()
        if status_clean in ("true", "active", "1"):
            query = query.filter(Item.status == True)
        elif status_clean in ("false", "inactive", "0"):
            query = query.filter(Item.status == False)

    # Category filter
    if category:
        query = query.filter(Item.category.ilike(f"%{category.strip()}%"))

    # Search filter (name, item_code, brand, description, hsn_code)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Item.name.ilike(search_pattern),
                Item.item_code.ilike(search_pattern),
                Item.brand.ilike(search_pattern),
                Item.description.ilike(search_pattern),
                Item.hsn_code.ilike(search_pattern),
            )
        )

    total = query.count()
    items = query.order_by(Item.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_item(db: Session, obj_in: ItemCreate) -> Item:
    """Create a new item master with auto-generated code."""
    code = generate_item_code(db)
    db_obj = Item(
        item_code=code,
        name=obj_in.name,
        brand=obj_in.brand,
        description=obj_in.description,
        category=obj_in.category,
        unit=obj_in.unit,
        hsn_code=obj_in.hsn_code,
        tax_percent=obj_in.tax_percent,
        last_purchase_rate=obj_in.last_purchase_rate,
        status=True,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_item(db: Session, db_obj: Item, obj_in: ItemUpdate) -> Item:
    """Update existing item details."""
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_item_status(db: Session, db_obj: Item, status: bool) -> Item:
    """Activate or deactivate an item (soft delete)."""
    db_obj.status = status
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

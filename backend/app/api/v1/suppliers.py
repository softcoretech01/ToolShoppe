from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.crud.supplier import (
    get_supplier_by_id,
    get_supplier_by_name,
    get_supplier_by_email,
    get_suppliers,
    create_supplier,
    update_supplier,
    update_supplier_status,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierStatusUpdate, SupplierOut
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/suppliers", tags=["1. Masters - Suppliers"])


@router.post(
    "",
    response_model=SuccessResponse[SupplierOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create Supplier",
    description="Create a new supplier master record with auto-generated code."
)
def create_new_supplier(
    supplier_in: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = create_supplier(db, supplier_in)
    return SuccessResponse(
        success=True,
        message="Supplier created successfully",
        data=SupplierOut.model_validate(supplier),
    )


@router.get(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="List Suppliers",
    description="Retrieve suppliers with optional search term, status filter ('active', 'inactive', 'all'), and pagination."
)
def list_suppliers(
    search: Optional[str] = Query(None, description="Search by supplier name, code, contact person, categories, or email"),
    status: Optional[str] = Query("all", description="Filter by status: 'active', 'inactive', or 'all'"),
    skip: int = Query(0, ge=0, description="Records to skip for pagination"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_suppliers(db, skip=skip, limit=limit, search=search, status=status)
    return SuccessResponse(
        success=True,
        message="Suppliers retrieved successfully",
        data={
            "items": [SupplierOut.model_validate(s) for s in items],
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    )


@router.get(
    "/{supplier_name}",
    response_model=SuccessResponse[SupplierOut],
    summary="Get Supplier Details",
    description="Retrieve a single supplier by their name, code, or numeric ID."
)
def get_supplier(
    supplier_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = get_supplier_by_name(db, supplier_name)
    if not supplier and supplier_name.isdigit():
        supplier = get_supplier_by_id(db, int(supplier_name))
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier '{supplier_name}' not found.",
        )
    return SuccessResponse(
        success=True,
        message="Supplier details retrieved successfully",
        data=SupplierOut.model_validate(supplier),
    )


@router.put(
    "/{supplier_name}",
    response_model=SuccessResponse[SupplierOut],
    summary="Update Supplier",
    description="Update fields of an existing supplier by name, code, or numeric ID."
)
def update_existing_supplier(
    supplier_name: str,
    supplier_in: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = get_supplier_by_name(db, supplier_name)
    if not supplier and supplier_name.isdigit():
        supplier = get_supplier_by_id(db, int(supplier_name))
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier '{supplier_name}' not found.",
        )

    updated = update_supplier(db, supplier, supplier_in)
    return SuccessResponse(
        success=True,
        message="Supplier updated successfully",
        data=SupplierOut.model_validate(updated),
    )


@router.patch(
    "/{supplier_name}/status",
    response_model=SuccessResponse[SupplierOut],
    summary="Toggle Supplier Status (Soft Delete)",
    description="Activate or deactivate a supplier by name, code, or numeric ID."
)
def change_supplier_status(
    supplier_name: str,
    status_in: SupplierStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = get_supplier_by_name(db, supplier_name)
    if not supplier and supplier_name.isdigit():
        supplier = get_supplier_by_id(db, int(supplier_name))
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier '{supplier_name}' not found.",
        )

    updated = update_supplier_status(db, supplier, status_in.status)
    status_label = "activated" if status_in.status else "deactivated"
    return SuccessResponse(
        success=True,
        message=f"Supplier has been {status_label} successfully",
        data=SupplierOut.model_validate(updated),
    )


@router.patch(
    "/{supplier_name}/toggle-status",
    response_model=SuccessResponse[SupplierOut],
    summary="Toggle Supplier Status",
    description="Toggle active/inactive status of a supplier."
)
def toggle_supplier_status(
    supplier_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = get_supplier_by_name(db, supplier_name)
    if not supplier and supplier_name.isdigit():
        supplier = get_supplier_by_id(db, int(supplier_name))
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier '{supplier_name}' not found.",
        )

    updated = update_supplier_status(db, supplier, not supplier.status)
    status_label = "activated" if updated.status else "deactivated"
    return SuccessResponse(
        success=True,
        message=f"Supplier has been {status_label} successfully",
        data=SupplierOut.model_validate(updated),
    )

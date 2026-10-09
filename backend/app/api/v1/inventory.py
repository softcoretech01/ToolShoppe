from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.inventory import (
    StockLedgerListOut, StockSummaryListOut, ItemInventoryOut
)
from app.schemas.response import SuccessResponse
from app.crud.inventory import (
    get_stock_ledger, get_stock_summaries, get_item_inventory,
    format_stock_ledger_out, format_stock_summary_out
)

router = APIRouter(prefix="/inventory", tags=["4. Inventory"])


@router.get(
    "/ledger",
    response_model=SuccessResponse[StockLedgerListOut],
    summary="List Stock Ledger Movements",
    description="Retrieve chronological stock ledger entries with pagination and optional filters.",
)
def list_stock_ledger(
    customer_request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    item_id: Optional[int] = Query(None, description="Filter by Item ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_stock_ledger(
        db=db,
        customer_request_id=customer_request_id,
        item_id=item_id,
        skip=skip,
        limit=limit,
    )
    data = StockLedgerListOut(
        total=total,
        items=[format_stock_ledger_out(entry) for entry in items],
    )
    return SuccessResponse(
        success=True,
        message="Stock ledger entries retrieved successfully.",
        data=data,
    )


@router.get(
    "/summary",
    response_model=SuccessResponse[StockSummaryListOut],
    summary="List Stock Summary",
    description="Retrieve stock summary balances grouped by Customer Request and Item.",
)
def list_stock_summary(
    customer_request_id: Optional[int] = Query(None, description="Filter by Customer Request ID"),
    item_id: Optional[int] = Query(None, description="Filter by Item ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_stock_summaries(
        db=db,
        customer_request_id=customer_request_id,
        item_id=item_id,
        skip=skip,
        limit=limit,
    )
    data = StockSummaryListOut(
        total=total,
        items=[format_stock_summary_out(s) for s in items],
    )
    return SuccessResponse(
        success=True,
        message="Stock summaries retrieved successfully.",
        data=data,
    )


@router.get(
    "/item/{item_id}",
    response_model=SuccessResponse[ItemInventoryOut],
    summary="Get Item Inventory Details",
    description="Retrieve full inventory status for an item including on-hand stock across requests, last purchase rate, and ledger trail.",
)
def get_item_inventory_details(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = get_item_inventory(db=db, item_id=item_id)
        return SuccessResponse(
            success=True,
            message="Item inventory details retrieved successfully.",
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

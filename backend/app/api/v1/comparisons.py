from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.quotation_comparison import (
    ComparisonMatrixOut, ComparisonApproveRequest
)
from app.schemas.response import SuccessResponse
from app.crud.quotation_comparison import (
    build_comparison_matrix, approve_comparison
)

router = APIRouter(prefix="/purchase/compare", tags=["3. Purchase - Quotation Comparison"])


@router.get(
    "/{pr_id}",
    response_model=SuccessResponse[ComparisonMatrixOut],
    summary="Get Quotation Comparison Matrix",
    description=(
        "Retrieve comparative statement for all quotations submitted for a Purchase Request. "
        "Calculates lowest rate per item, lowest grand total, and computes recommended best supplier "
        "using 4-tier recommendation decision logic (filtering out incomplete quotes)."
    )
)
def get_comparison(
    pr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        matrix = build_comparison_matrix(db, pr_id)
        return SuccessResponse(
            success=True,
            message="Quotation comparison statement generated successfully.",
            data=matrix,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post(
    "/{pr_id}/approve",
    response_model=SuccessResponse[ComparisonMatrixOut],
    summary="Approve Best Supplier Quotation",
    description=(
        "Approve the selected supplier quotation. If selecting a supplier other than the recommended "
        "best quotation, an override reason is mandatory. "
        "Upon approval, marks the selected quotation as 'Selected', rejects others, updates PR to 'Quoted', "
        "and sets Customer Request status to 'Approved'."
    )
)
def approve_supplier_quote(
    pr_id: int,
    approve_in: ComparisonApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        matrix = approve_comparison(
            db=db,
            pr_id=pr_id,
            selected_supplier_id=approve_in.selected_supplier_id,
            override_reason=approve_in.override_reason,
        )
        return SuccessResponse(
            success=True,
            message="Supplier quotation approved successfully. Sourcing workflow completed.",
            data=matrix,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

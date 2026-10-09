"""
Dashboard API Endpoints
Real-time KPIs, Needs Attention alerts, workflow summary, and analytics charts.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.response import SuccessResponse
from app.schemas.dashboard import (
    DashboardOut, KPICardsOut, DashboardChartsOut,
    NeedsAttentionItem, WorkflowSummaryOut
)
from app.crud.dashboard import (
    get_dashboard, get_kpi_cards, get_dashboard_charts,
    get_needs_attention, get_workflow_summary
)

router = APIRouter(prefix="/sales/dashboard", tags=["0. Dashboard & Analytics"])
api_alias_router = APIRouter(prefix="/api/dashboard", tags=["0. Dashboard & Analytics"])
root_alias_router = APIRouter(prefix="/dashboard", tags=["0. Dashboard & Analytics"])


@router.get("", response_model=SuccessResponse[DashboardOut], summary="Get Complete Dashboard Overview")
@api_alias_router.get("", response_model=SuccessResponse[DashboardOut], summary="Get Complete Dashboard Overview")
@root_alias_router.get("", response_model=SuccessResponse[DashboardOut], summary="Get Complete Dashboard Overview")
def get_full_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full dashboard data including KPIs, alerts, workflow summary, and charts."""
    data = get_dashboard(db)
    return SuccessResponse(
        success=True,
        message="Dashboard data retrieved successfully.",
        data=data,
    )


@router.get("/kpi", response_model=SuccessResponse[KPICardsOut], summary="Get Dashboard KPI Cards")
@api_alias_router.get("/kpi", response_model=SuccessResponse[KPICardsOut], summary="Get Dashboard KPI Cards")
@root_alias_router.get("/kpi", response_model=SuccessResponse[KPICardsOut], summary="Get Dashboard KPI Cards")
def get_kpis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve real-time business KPI metrics."""
    data = get_kpi_cards(db)
    return SuccessResponse(
        success=True,
        message="KPI metrics retrieved successfully.",
        data=data,
    )


@router.get("/charts", response_model=SuccessResponse[DashboardChartsOut], summary="Get Dashboard Analytics Charts")
@api_alias_router.get("/charts", response_model=SuccessResponse[DashboardChartsOut], summary="Get Dashboard Analytics Charts")
@root_alias_router.get("/charts", response_model=SuccessResponse[DashboardChartsOut], summary="Get Dashboard Analytics Charts")
def get_charts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve chart series: Sales vs Purchase, Work waiting by stage, Best sellers, Margin trend."""
    data = get_dashboard_charts(db)
    return SuccessResponse(
        success=True,
        message="Dashboard charts retrieved successfully.",
        data=data,
    )


@router.get("/needs-attention", response_model=SuccessResponse[List[NeedsAttentionItem]], summary="Get Actionable Needs Attention Alerts")
@api_alias_router.get("/needs-attention", response_model=SuccessResponse[List[NeedsAttentionItem]], summary="Get Actionable Needs Attention Alerts")
@root_alias_router.get("/needs-attention", response_model=SuccessResponse[List[NeedsAttentionItem]], summary="Get Actionable Needs Attention Alerts")
def get_attention(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve actionable items requiring operator attention."""
    data = get_needs_attention(db)
    return SuccessResponse(
        success=True,
        message="Needs attention items retrieved successfully.",
        data=data,
    )


@router.get("/workflow-summary", response_model=SuccessResponse[WorkflowSummaryOut], summary="Get Workflow Summary Counts")
@api_alias_router.get("/workflow-summary", response_model=SuccessResponse[WorkflowSummaryOut], summary="Get Workflow Summary Counts")
@root_alias_router.get("/workflow-summary", response_model=SuccessResponse[WorkflowSummaryOut], summary="Get Workflow Summary Counts")
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve total document counts across the entire 11+ step workflow."""
    data = get_workflow_summary(db)
    return SuccessResponse(
        success=True,
        message="Workflow summary counts retrieved successfully.",
        data=data,
    )

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import CostItem
from backend.app.services.allocation_service import AllocationService
from backend.app.services.anomaly_detector import AnomalyDetectorService
from backend.app.services.budget_service import BudgetService
from backend.app.services.cost_analyzer import CostAnalyzerService
from backend.app.services.finops_engine import FinOpsEngine
from backend.app.services.gpu_service import GpuService
from backend.app.security import require_permissions, AuthContext

router = APIRouter(prefix="/billing", tags=["Billing & Costs"])


class BudgetCreateRequest(BaseModel):
    name: str
    amount: float = Field(gt=0)
    period: str = "monthly"
    provider_filter: Optional[str] = "All"
    service_filter: Optional[str] = None
    alert_threshold_warning: float = 75.0
    alert_threshold_critical: float = 90.0

@router.get("/summary")
def get_cost_summary(
    days: int = Query(30, description="Nombre de jours à analyser"),
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db)
):
    return CostAnalyzerService.get_cost_summary(db, ctx.tenant_id, days)

@router.get("/providers")
def get_cost_by_provider(
    days: int = Query(30, description="Nombre de jours à analyser"),
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db)
):
    return CostAnalyzerService.get_cost_by_provider(db, ctx.tenant_id, days)

@router.get("/trend")
def get_cost_trend(
    days: int = Query(30, description="Nombre de jours à analyser"),
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db)
):
    return CostAnalyzerService.get_cost_trend(db, ctx.tenant_id, days)

@router.get("/kubernetes")
def get_kubernetes_metrics(
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db)
):
    return CostAnalyzerService.get_kubernetes_efficiency(db, ctx.tenant_id)

@router.get("/anomalies")
def get_anomalies(
    status: str = Query(None, description="Filtrer par statut d'anomalie"),
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db)
):
    return AnomalyDetectorService.get_anomalies(db, ctx.tenant_id, status)

@router.post("/anomalies/{anomaly_id}/resolve")
def resolve_anomaly(
    anomaly_id: str,
    status: str = "Resolved",
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db)
):
    success = AnomalyDetectorService.update_anomaly_status(db, ctx.tenant_id, anomaly_id, status)
    return {"success": success, "status": status}


@router.get("/forecast")
def get_cost_forecast(
    days: int = Query(30, ge=7, le=90),
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    CostAnalyzerService.seed_data_if_empty(db, ctx.tenant_id)
    return BudgetService.get_forecast(db, ctx.tenant_id, days)


@router.get("/budgets")
def list_budgets(
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    CostAnalyzerService.seed_data_if_empty(db, ctx.tenant_id)
    return BudgetService.list_budgets(db, ctx.tenant_id)


@router.post("/budgets")
def create_budget(
    body: BudgetCreateRequest,
    ctx: AuthContext = Depends(require_permissions("reports:write")),
    db: Session = Depends(get_db),
):
    budget = BudgetService.create_budget(
        db,
        ctx.tenant_id,
        ctx.username,
        body.name,
        body.amount,
        body.period,
        body.provider_filter,
        body.service_filter,
        body.alert_threshold_warning,
        body.alert_threshold_critical,
    )
    return {"success": True, "budget": BudgetService._serialize(budget)}


@router.get("/allocation")
def get_cost_allocation(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("team", description="team|env|cost_center|product|owner"),
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    CostAnalyzerService.seed_data_if_empty(db, ctx.tenant_id)
    return AllocationService.get_allocation(db, ctx.tenant_id, days, group_by)


@router.get("/showback")
def get_showback(
    days: int = Query(30, ge=1, le=365),
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    CostAnalyzerService.seed_data_if_empty(db, ctx.tenant_id)
    return AllocationService.get_chargeback_summary(db, ctx.tenant_id, days)


@router.post("/finops/analyze")
def run_finops_analysis(
    ctx: AuthContext = Depends(require_permissions("optimization:write")),
    db: Session = Depends(get_db),
):
    if db.query(CostItem).filter(CostItem.tenant_id == ctx.tenant_id).count() == 0:
        raise HTTPException(
            status_code=400,
            detail="Aucune donnée de coût. Connectez un cloud ou importez un CSV.",
        )
    result = FinOpsEngine.run_full_analysis(db, ctx.tenant_id)
    return {"success": True, **result}


@router.get("/gpu")
def get_gpu_analytics(
    days: int = Query(30, ge=7, le=90),
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    CostAnalyzerService.seed_data_if_empty(db, ctx.tenant_id)
    data = GpuService.get_gpu_workload_analytics(db, ctx.tenant_id, days)
    total = (
        db.query(func.sum(CostItem.cost))
        .filter(CostItem.tenant_id == ctx.tenant_id)
        .scalar()
        or 0
    )
    if total and data["total_gpu_ai_cost"]:
        data["share_of_cloud_pct"] = round(data["total_gpu_ai_cost"] / float(total) * 100, 1)
    return data

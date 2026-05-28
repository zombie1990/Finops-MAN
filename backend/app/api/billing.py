from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.services.cost_analyzer import CostAnalyzerService
from backend.app.services.anomaly_detector import AnomalyDetectorService
from backend.app.security import require_permissions, AuthContext

router = APIRouter(prefix="/billing", tags=["Billing & Costs"])

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

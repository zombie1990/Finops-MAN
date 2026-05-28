from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.security import AuthContext, require_permissions
from backend.app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts & Observability"])


@router.get("/rules")
def list_alert_rules(
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    return AlertService.list_rules(db, ctx.tenant_id)


@router.get("/events")
def list_alert_events(
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    return AlertService.list_events(db, ctx.tenant_id)


@router.post("/evaluate")
def evaluate_alerts(
    ctx: AuthContext = Depends(require_permissions("optimization:write")),
    db: Session = Depends(get_db),
):
    fired = AlertService.evaluate_and_fire(db, ctx.tenant_id)
    return {"success": True, "events_fired": fired}


@router.post("/events/{event_id}/acknowledge")
def acknowledge_alert(
    event_id: str,
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    ok = AlertService.acknowledge_event(db, ctx.tenant_id, event_id)
    return {"success": ok}

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import Connector, SyncSchedule
from backend.app.security import AuthContext, require_permissions

router = APIRouter(prefix="/schedules", tags=["Sync Schedules"])


class ScheduleUpsertRequest(BaseModel):
    connector_id: str
    enabled: bool = True
    interval_minutes: int = Field(default=360, ge=15, le=10080)


@router.get("")
def list_schedules(
    ctx: AuthContext = Depends(require_permissions("connectors:read")),
    db: Session = Depends(get_db),
):
    rows = db.query(SyncSchedule).filter(SyncSchedule.tenant_id == ctx.tenant_id).all()
    return [
        {
            "id": s.id,
            "connector_id": s.connector_id,
            "enabled": s.enabled,
            "interval_minutes": s.interval_minutes,
            "last_run_at": s.last_run_at.strftime("%Y-%m-%d %H:%M") if s.last_run_at else None,
            "next_run_at": s.next_run_at.strftime("%Y-%m-%d %H:%M") if s.next_run_at else None,
        }
        for s in rows
    ]


@router.post("")
def upsert_schedule(
    request: ScheduleUpsertRequest,
    ctx: AuthContext = Depends(require_permissions("connectors:write")),
    db: Session = Depends(get_db),
):
    connector = (
        db.query(Connector)
        .filter(Connector.tenant_id == ctx.tenant_id, Connector.id == request.connector_id)
        .first()
    )
    if not connector:
        raise HTTPException(status_code=404, detail="Connecteur introuvable.")

    schedule = (
        db.query(SyncSchedule)
        .filter(
            SyncSchedule.tenant_id == ctx.tenant_id,
            SyncSchedule.connector_id == request.connector_id,
        )
        .first()
    )
    now = datetime.utcnow()
    if not schedule:
        schedule = SyncSchedule(
            id=str(uuid.uuid4()),
            tenant_id=ctx.tenant_id,
            connector_id=request.connector_id,
            enabled=request.enabled,
            interval_minutes=request.interval_minutes,
            next_run_at=now,
        )
        db.add(schedule)
    else:
        schedule.enabled = request.enabled
        schedule.interval_minutes = request.interval_minutes
        schedule.next_run_at = now
    db.commit()
    return {"success": True, "schedule_id": schedule.id}

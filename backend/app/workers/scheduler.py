from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models import Connector, SyncSchedule
from backend.app.services.connector_service import ConnectorService

_scheduler = None


def _sync_due_connectors():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        connectors = (
            db.query(Connector)
            .filter(Connector.status.in_(["Connected", "Error"]))
            .all()
        )
        for connector in connectors:
            schedule = (
                db.query(SyncSchedule)
                .filter(
                    SyncSchedule.connector_id == connector.id,
                    SyncSchedule.enabled == True,  # noqa: E712
                )
                .first()
            )
            interval = schedule.interval_minutes if schedule else settings.SYNC_DEFAULT_INTERVAL_MINUTES
            if schedule and schedule.next_run_at and schedule.next_run_at > now:
                continue
            if connector.last_sync_at and connector.last_sync_at > now - timedelta(minutes=interval):
                continue

            ConnectorService.sync_connector(
                db,
                connector.tenant_id,
                "scheduler",
                connector.id,
                days=30,
            )
            if schedule:
                schedule.last_run_at = now
                schedule.next_run_at = now + timedelta(minutes=interval)
            db.commit()
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if not settings.SYNC_SCHEDULER_ENABLED:
        return None
    if _scheduler and _scheduler.running:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _sync_due_connectors,
        "interval",
        minutes=max(15, settings.SYNC_DEFAULT_INTERVAL_MINUTES),
        id="connector_sync_job",
        replace_existing=True,
    )
    _scheduler.start()
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None

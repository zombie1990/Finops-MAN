import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import AlertEvent, AlertRule, Budget, CostItem
from backend.app.services.budget_service import BudgetService


class AlertService:
    @staticmethod
    def ensure_default_rules(db: Session, tenant_id: str) -> None:
        if db.query(AlertRule).filter(AlertRule.tenant_id == tenant_id).count() > 0:
            return
        defaults = [
            ("Budget 75%", "budget_overrun", "gt", 75.0),
            ("Budget 90%", "budget_overrun", "gt", 90.0),
            ("Spike coût journalier", "cost_threshold", "gt", 5000.0),
            ("Anomalie critique", "anomaly", "gt", 1.0),
        ]
        for name, atype, cond, thresh in defaults:
            db.add(
                AlertRule(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    name=name,
                    alert_type=atype,
                    condition=cond,
                    threshold_value=thresh,
                    enabled=True,
                )
            )
        db.commit()

    @staticmethod
    def list_rules(db: Session, tenant_id: str) -> List[Dict]:
        AlertService.ensure_default_rules(db, tenant_id)
        rules = db.query(AlertRule).filter(AlertRule.tenant_id == tenant_id).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "alert_type": r.alert_type,
                "condition": r.condition,
                "threshold_value": r.threshold_value,
                "enabled": r.enabled,
                "provider_filter": r.provider_filter,
            }
            for r in rules
        ]

    @staticmethod
    def list_events(db: Session, tenant_id: str, limit: int = 50) -> List[Dict]:
        events = (
            db.query(AlertEvent)
            .filter(AlertEvent.tenant_id == tenant_id)
            .order_by(AlertEvent.triggered_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": e.id,
                "rule_id": e.rule_id,
                "severity": e.severity,
                "title": e.title,
                "description": e.description,
                "current_value": e.current_value,
                "threshold_value": e.threshold_value,
                "status": e.status,
                "triggered_at": e.triggered_at.strftime("%Y-%m-%d %H:%M"),
            }
            for e in events
        ]

    @staticmethod
    def _event_exists_recent(db: Session, tenant_id: str, title: str, hours: int = 24) -> bool:
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            db.query(AlertEvent)
            .filter(
                AlertEvent.tenant_id == tenant_id,
                AlertEvent.title == title,
                AlertEvent.triggered_at >= since,
            )
            .first()
            is not None
        )

    @staticmethod
    def evaluate_and_fire(db: Session, tenant_id: str) -> int:
        AlertService.ensure_default_rules(db, tenant_id)
        fired = 0

        budgets = db.query(Budget).filter(Budget.tenant_id == tenant_id).all()
        for b in budgets:
            BudgetService.refresh_budget_metrics(db, b)
            pct = (b.forecast / b.amount * 100) if b.amount > 0 else 0
            for threshold, sev in [(75, "Medium"), (90, "High"), (100, "Critical")]:
                if pct >= threshold:
                    title = f"Budget {b.name}: {pct:.0f}% prévu"
                    if AlertService._event_exists_recent(db, tenant_id, title):
                        continue
                    rule = (
                        db.query(AlertRule)
                        .filter(
                            AlertRule.tenant_id == tenant_id,
                            AlertRule.alert_type == "budget_overrun",
                            AlertRule.threshold_value == float(threshold),
                        )
                        .first()
                    )
                    db.add(
                        AlertEvent(
                            id=str(uuid.uuid4()),
                            tenant_id=tenant_id,
                            rule_id=rule.id if rule else str(uuid.uuid4()),
                            severity=sev,
                            title=title,
                            description=f"Dépensé {b.spent}$ — prévision {b.forecast}$ / {b.amount}$",
                            current_value=pct,
                            threshold_value=threshold,
                            status="Active",
                        )
                    )
                    fired += 1

        today = datetime.utcnow().date()
        start = datetime.combine(today, datetime.min.time())
        daily = (
            db.query(func.sum(CostItem.cost))
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= start)
            .scalar()
            or 0
        )
        if float(daily) > 5000:
            title = f"Spike coût journalier: {daily:.0f} $"
            if not AlertService._event_exists_recent(db, tenant_id, title):
                db.add(
                    AlertEvent(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        rule_id=str(uuid.uuid4()),
                        severity="High",
                        title=title,
                        description="Dépense du jour au-dessus du seuil configuré.",
                        current_value=float(daily),
                        threshold_value=5000.0,
                        status="Active",
                    )
                )
                fired += 1

        db.commit()
        return fired

    @staticmethod
    def acknowledge_event(db: Session, tenant_id: str, event_id: str) -> bool:
        event = (
            db.query(AlertEvent)
            .filter(AlertEvent.tenant_id == tenant_id, AlertEvent.id == event_id)
            .first()
        )
        if not event:
            return False
        event.status = "Acknowledged"
        event.acknowledged_at = datetime.utcnow()
        db.commit()
        return True

import uuid
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import Anomaly, AuditLog, CostItem, Recommendation, Report


class ReportService:
    @staticmethod
    def list_reports(db: Session, tenant_id: str) -> List[Dict]:
        reports = (
            db.query(Report)
            .filter(Report.tenant_id == tenant_id)
            .order_by(Report.generated_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "report_type": r.report_type,
                "title": r.title,
                "status": r.status,
                "period_days": r.period_days,
                "summary": r.summary,
                "generated_at": r.generated_at.strftime("%Y-%m-%d %H:%M"),
                "download_count": r.download_count,
            }
            for r in reports
        ]

    @staticmethod
    def generate_report(db: Session, tenant_id: str, username: str, report_type: str, period_days: int) -> Dict:
        now = datetime.utcnow()
        since = now - timedelta(days=period_days)
        report_id = str(uuid.uuid4())

        total_cost = (
            db.query(func.coalesce(func.sum(CostItem.cost), 0.0))
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= since)
            .scalar()
            or 0.0
        )
        total_savings = (
            db.query(func.coalesce(func.sum(Recommendation.estimated_saving), 0.0))
            .filter(Recommendation.tenant_id == tenant_id, Recommendation.status == "Pending")
            .scalar()
            or 0.0
        )
        unresolved_anomalies = (
            db.query(func.count(Anomaly.id))
            .filter(Anomaly.tenant_id == tenant_id, Anomaly.status != "Resolved")
            .scalar()
            or 0
        )

        if report_type not in {"executive", "technical", "savings", "carbon"}:
            raise ValueError("report_type invalide.")

        summary = (
            f"Periode {period_days}j: cout total {round(total_cost, 2)} $, "
            f"economies potentielles {round(total_savings, 2)} $, "
            f"anomalies ouvertes {unresolved_anomalies}."
        )
        content_json = {
            "kpis": {
                "total_cost": round(total_cost, 2),
                "potential_savings": round(total_savings, 2),
                "unresolved_anomalies": unresolved_anomalies,
                "roi_months": round((total_savings / total_cost), 3) if total_cost else 0.0,
            },
            "insights": [
                "Prioriser les recommandations a fort impact et faible risque.",
                "Traiter les anomalies critiques en moins de 24h.",
                "Mettre en place des budgets par equipe avec alertes progressives.",
            ],
            "actions": [
                {"name": "Rightsizing compute", "priority": "High"},
                {"name": "Cleanup snapshots orphelins", "priority": "Medium"},
                {"name": "Optimisation Kubernetes requests/limits", "priority": "High"},
            ],
        }

        report = Report(
            id=report_id,
            tenant_id=tenant_id,
            report_type=report_type,
            title=f"{report_type.title()} FinOps Report ({period_days}j)",
            status="Ready",
            period_days=period_days,
            summary=summary,
            content_json=content_json,
            generated_at=now,
            download_count=0,
        )
        db.add(report)

        db.add(
            AuditLog(
                tenant_id=tenant_id,
                action="report_generated",
                user=username,
                resource_type="report",
                resource_id=report_id,
                details=f"type={report_type};period={period_days}",
                timestamp=now,
            )
        )
        db.commit()

        return {
            "success": True,
            "report_id": report_id,
            "status": "Ready",
            "summary": summary,
        }

    @staticmethod
    def get_report(db: Session, tenant_id: str, report_id: str) -> Dict:
        report = db.query(Report).filter(Report.tenant_id == tenant_id, Report.id == report_id).first()
        if not report:
            return {"success": False, "message": "Rapport introuvable."}

        report.download_count = (report.download_count or 0) + 1
        db.commit()
        return {
            "id": report.id,
            "report_type": report.report_type,
            "title": report.title,
            "status": report.status,
            "period_days": report.period_days,
            "summary": report.summary,
            "content": report.content_json or {},
            "generated_at": report.generated_at.strftime("%Y-%m-%d %H:%M"),
            "download_count": report.download_count,
        }

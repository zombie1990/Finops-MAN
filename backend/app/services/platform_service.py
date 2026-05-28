from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import Connector, CostItem, ScanResult


class PlatformService:
    @staticmethod
    def get_status(db: Session, tenant_id: str) -> dict:
        cost_count = db.query(func.count(CostItem.id)).filter(CostItem.tenant_id == tenant_id).scalar() or 0
        connectors = db.query(Connector).filter(Connector.tenant_id == tenant_id).all()
        connected = [c for c in connectors if c.status == "Connected"]
        last_import = (
            db.query(ScanResult)
            .filter(ScanResult.tenant_id == tenant_id)
            .order_by(ScanResult.uploaded_at.desc())
            .first()
        )
        return {
            "environment": settings.APP_ENV,
            "demo_mode": settings.USE_DEMO_DATA,
            "data_mode": "demo" if settings.USE_DEMO_DATA else "production",
            "cost_records": int(cost_count),
            "connectors_total": len(connectors),
            "connectors_connected": len(connected),
            "has_real_data": int(cost_count) > 0 and not settings.USE_DEMO_DATA,
            "last_csv_import": last_import.uploaded_at.strftime("%Y-%m-%d %H:%M") if last_import else None,
            "message": (
                "Mode demonstration actif (donnees fictives possibles)."
                if settings.USE_DEMO_DATA
                else "Mode production: connectez AWS/Azure/GCP ou importez un CSV."
            ),
        }

import uuid
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.app.connectors.base import CloudSyncResult
from backend.app.connectors.factory import sync_cloud_connector, test_cloud_connector
from backend.app.config import settings
from backend.app.models import AuditLog, CloudAccount, Connector, CostItem, SyncSchedule, Tenant


def _redact_config(config: Dict[str, Any]) -> Dict[str, Any]:
    if not config:
        return {}
    redacted = {}
    sensitive_markers = ("secret", "password", "key", "token", "credentials", "private")
    for key, value in config.items():
        lower = key.lower()
        if any(marker in lower for marker in sensitive_markers):
            redacted[key] = "***configured***"
        else:
            redacted[key] = value
    return redacted


def _ensure_tenant(db: Session, tenant_id: str) -> None:
    if not db.query(Tenant).filter(Tenant.id == tenant_id).first():
        db.add(Tenant(id=tenant_id, name="Default Tenant", created_at=datetime.utcnow()))
        db.commit()


class ConnectorService:
    REAL_CLOUD_PROVIDERS = {"AWS", "Azure", "GCP"}
    SUPPORTED_PROVIDERS = {
        "AWS": {"types": {"billing_api", "cost_export"}},
        "Azure": {"types": {"billing_api"}},
        "GCP": {"types": {"billing_api", "cost_export"}},
        "Kubernetes": {"types": {"metrics_api"}},
        "VMware": {"types": {"metrics_api"}},
        "Datadog": {"types": {"metrics_api"}},
        "Prometheus": {"types": {"metrics_api"}},
        "Snowflake": {"types": {"billing_api"}},
        "OpenAI": {"types": {"billing_api"}},
        "GitHub": {"types": {"billing_api"}},
    }

    @staticmethod
    def list_connectors(db: Session, tenant_id: str) -> List[Dict]:
        items = (
            db.query(Connector)
            .filter(Connector.tenant_id == tenant_id)
            .order_by(Connector.created_at.desc())
            .all()
        )
        return [
            {
                "id": item.id,
                "provider": item.provider,
                "name": item.name,
                "connector_type": item.connector_type,
                "status": item.status,
                "last_sync_at": item.last_sync_at.strftime("%Y-%m-%d %H:%M") if item.last_sync_at else None,
                "last_sync_items": item.last_sync_items,
                "last_error": item.last_error,
                "config_json": _redact_config(item.config_json or {}),
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for item in items
        ]

    @staticmethod
    def create_connector(
        db: Session,
        tenant_id: str,
        username: str,
        provider: str,
        name: str,
        connector_type: str,
        config_json: Dict,
    ) -> Dict:
        _ensure_tenant(db, tenant_id)
        normalized_provider = provider.strip()
        if normalized_provider not in ConnectorService.SUPPORTED_PROVIDERS:
            raise ValueError(f"Provider non supporte: {normalized_provider}")

        valid_types = ConnectorService.SUPPORTED_PROVIDERS[normalized_provider]["types"]
        if connector_type not in valid_types:
            raise ValueError(
                f"Type de connecteur invalide pour {normalized_provider}. Valeurs autorisees: {sorted(valid_types)}"
            )

        connector_id = str(uuid.uuid4())
        connector = Connector(
            id=connector_id,
            tenant_id=tenant_id,
            provider=normalized_provider,
            name=name,
            connector_type=connector_type,
            status="Disconnected",
            config_json=config_json or {},
            created_at=datetime.utcnow(),
        )
        db.add(connector)

        account_id = config_json.get("account_id") or config_json.get("subscription_id") or config_json.get("project_id") or connector_id
        if not db.query(CloudAccount).filter(CloudAccount.id == str(account_id)).first():
            db.add(
                CloudAccount(
                    id=str(account_id),
                    tenant_id=tenant_id,
                    provider=normalized_provider,
                    name=name,
                    status="Active",
                    credentials=None,
                    created_at=datetime.utcnow(),
                )
            )

        if normalized_provider in ConnectorService.REAL_CLOUD_PROVIDERS:
            test_result = test_cloud_connector(normalized_provider, config_json or {})
            connector.status = "Connected" if test_result.success else "Error"
            connector.last_error = test_result.error
        else:
            connector.status = "Connected"

        db.add(
            SyncSchedule(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                connector_id=connector_id,
                enabled=True,
                interval_minutes=settings.SYNC_DEFAULT_INTERVAL_MINUTES,
                next_run_at=datetime.utcnow(),
            )
        )
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                action="connector_created",
                user=username,
                resource_type="connector",
                resource_id=connector.id,
                details=f"{normalized_provider}:{connector_type}:{name}",
                timestamp=datetime.utcnow(),
            )
        )
        db.commit()
        return {
            "success": True,
            "connector_id": connector.id,
            "status": connector.status,
            "message": "Connecteur enregistre.",
            "last_error": connector.last_error,
        }

    @staticmethod
    def test_connector(db: Session, tenant_id: str, connector_id: str) -> Dict:
        connector = (
            db.query(Connector)
            .filter(Connector.tenant_id == tenant_id, Connector.id == connector_id)
            .first()
        )
        if not connector:
            return {"success": False, "message": "Connecteur introuvable."}
        if connector.provider not in ConnectorService.REAL_CLOUD_PROVIDERS:
            return {"success": True, "message": f"Provider {connector.provider}: pas de test cloud natif."}

        result = test_cloud_connector(connector.provider, connector.config_json or {})
        connector.status = "Connected" if result.success else "Error"
        connector.last_error = result.error
        db.commit()
        return {
            "success": result.success,
            "message": result.message or result.error,
            "status": connector.status,
        }

    @staticmethod
    def delete_connector(db: Session, tenant_id: str, username: str, connector_id: str) -> Dict:
        connector = (
            db.query(Connector)
            .filter(Connector.tenant_id == tenant_id, Connector.id == connector_id)
            .first()
        )
        if not connector:
            return {"success": False, "message": "Connecteur introuvable."}
        db.delete(connector)
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                action="connector_deleted",
                user=username,
                resource_type="connector",
                resource_id=connector_id,
                details=connector.name,
                timestamp=datetime.utcnow(),
            )
        )
        db.commit()
        return {"success": True, "message": "Connecteur supprime."}

    @staticmethod
    def _persist_cost_rows(db: Session, tenant_id: str, rows: List[Dict]) -> int:
        count = 0
        for row in rows:
            item = CostItem(
                tenant_id=tenant_id,
                account_id=str(row["account_id"]),
                date=row["date"],
                provider=row["provider"],
                service=row["service"],
                resource_id=row.get("resource_id"),
                resource_name=row.get("resource_name"),
                region=row.get("region"),
                cost=float(row["cost"]),
                usage_quantity=float(row.get("usage_quantity") or 0),
                usage_unit=row.get("usage_unit"),
                tags=row.get("tags"),
                carbon_emissions=float(row.get("carbon_emissions") or 0),
            )
            db.add(item)
            count += 1
        return count

    @staticmethod
    def sync_connector(db: Session, tenant_id: str, username: str, connector_id: str, days: int = 30) -> Dict:
        connector = (
            db.query(Connector)
            .filter(Connector.tenant_id == tenant_id, Connector.id == connector_id)
            .first()
        )
        if not connector:
            return {"success": False, "message": "Connecteur introuvable."}

        connector.status = "Syncing"
        connector.last_error = None
        db.commit()

        try:
            if connector.provider in ConnectorService.REAL_CLOUD_PROVIDERS:
                result = sync_cloud_connector(
                    connector.provider,
                    connector.config_json or {},
                    days=days,
                )
            else:
                result = CloudSyncResult(
                    success=False,
                    error=f"Synchronisation cloud native non disponible pour {connector.provider}.",
                )

            if not result.success:
                connector.status = "Error"
                connector.last_error = result.error or "Echec de synchronisation."
                db.commit()
                return {
                    "success": False,
                    "connector_id": connector.id,
                    "status": connector.status,
                    "message": connector.last_error,
                }

            synced_items = ConnectorService._persist_cost_rows(db, tenant_id, result.cost_rows)
            connector.status = "Connected"
            connector.last_sync_items = synced_items
            connector.last_sync_at = datetime.utcnow()
            connector.last_error = None

            db.add(
                AuditLog(
                    tenant_id=tenant_id,
                    action="connector_synced",
                    user=username,
                    resource_type="connector",
                    resource_id=connector.id,
                    details=f"sync_items={synced_items};provider={connector.provider}",
                    timestamp=datetime.utcnow(),
                )
            )
            db.commit()
            return {
                "success": True,
                "connector_id": connector.id,
                "status": connector.status,
                "synced_items": synced_items,
                "last_sync_at": connector.last_sync_at.strftime("%Y-%m-%d %H:%M"),
                "message": result.message or "Synchronisation terminee.",
            }
        except Exception as exc:
            connector.status = "Error"
            connector.last_error = str(exc)
            db.commit()
            return {
                "success": False,
                "connector_id": connector.id,
                "status": connector.status,
                "message": str(exc),
            }

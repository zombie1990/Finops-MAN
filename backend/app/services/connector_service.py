import uuid
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from backend.app.models import AuditLog, Connector


class ConnectorService:
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
                "config_json": item.config_json or {},
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
        normalized_provider = provider.strip()
        if normalized_provider not in ConnectorService.SUPPORTED_PROVIDERS:
            raise ValueError(f"Provider non supporte: {normalized_provider}")

        valid_types = ConnectorService.SUPPORTED_PROVIDERS[normalized_provider]["types"]
        if connector_type not in valid_types:
            raise ValueError(
                f"Type de connecteur invalide pour {normalized_provider}. Valeurs autorisees: {sorted(valid_types)}"
            )

        connector = Connector(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            provider=normalized_provider,
            name=name,
            connector_type=connector_type,
            status="Connected",
            config_json=config_json or {},
            created_at=datetime.utcnow(),
        )
        db.add(connector)

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
            "message": "Connecteur cree et actif.",
        }

    @staticmethod
    def sync_connector(db: Session, tenant_id: str, username: str, connector_id: str) -> Dict:
        connector = (
            db.query(Connector)
            .filter(Connector.tenant_id == tenant_id, Connector.id == connector_id)
            .first()
        )
        if not connector:
            return {"success": False, "message": "Connecteur introuvable."}

        connector.status = "Syncing"
        db.commit()

        # Simulation deterministic d'une synchronisation incrémentale.
        synced_items = 120 if connector.connector_type == "billing_api" else 300
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
                details=f"sync_items={synced_items}",
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
            "message": "Synchronisation terminee.",
        }

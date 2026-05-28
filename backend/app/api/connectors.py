from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.security import AuthContext, require_permissions
from backend.app.services.connector_service import ConnectorService

router = APIRouter(prefix="/connectors", tags=["Cloud Connectors"])


class ConnectorCreateRequest(BaseModel):
    provider: str = Field(..., description="AWS|Azure|GCP|Kubernetes|VMware|Datadog|Prometheus|Snowflake|OpenAI|GitHub")
    name: str
    connector_type: str = Field(..., description="billing_api|metrics_api|cost_export")
    config_json: dict = Field(default_factory=dict)


@router.get("")
def list_connectors(
    ctx: AuthContext = Depends(require_permissions("connectors:read")),
    db: Session = Depends(get_db),
):
    return ConnectorService.list_connectors(db, ctx.tenant_id)


@router.post("")
def create_connector(
    request: ConnectorCreateRequest,
    ctx: AuthContext = Depends(require_permissions("connectors:write")),
    db: Session = Depends(get_db),
):
    try:
        return ConnectorService.create_connector(
            db=db,
            tenant_id=ctx.tenant_id,
            username=ctx.username,
            provider=request.provider,
            name=request.name,
            connector_type=request.connector_type,
            config_json=request.config_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{connector_id}/sync")
def sync_connector(
    connector_id: str,
    ctx: AuthContext = Depends(require_permissions("connectors:write")),
    db: Session = Depends(get_db),
):
    data = ConnectorService.sync_connector(db, ctx.tenant_id, ctx.username, connector_id)
    if not data["success"]:
        raise HTTPException(status_code=404, detail=data["message"])
    return data

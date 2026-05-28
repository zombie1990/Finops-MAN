from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.security import AuthContext, require_permissions
from backend.app.services.ingestion_job_service import IngestionJobService

router = APIRouter(prefix="/ingestion", tags=["Ingestion Pipeline"])


class IngestionJobCreateRequest(BaseModel):
    source_type: str = Field(..., description="aws_cur|azure_cost|gcp_billing|kubernetes|file_upload|openai_billing")
    source_ref: str = None
    max_retries: int = Field(default=3, ge=1, le=10)


@router.get("/jobs")
def list_jobs(
    ctx: AuthContext = Depends(require_permissions("connectors:read")),
    db: Session = Depends(get_db),
):
    return IngestionJobService.list_jobs(db, ctx.tenant_id)


@router.post("/jobs")
def create_job(
    request: IngestionJobCreateRequest,
    ctx: AuthContext = Depends(require_permissions("connectors:write")),
    db: Session = Depends(get_db),
):
    try:
        return IngestionJobService.create_job(
            db=db,
            tenant_id=ctx.tenant_id,
            username=ctx.username,
            source_type=request.source_type,
            source_ref=request.source_ref,
            max_retries=request.max_retries,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/run")
def run_job(
    job_id: str,
    ctx: AuthContext = Depends(require_permissions("connectors:write")),
    db: Session = Depends(get_db),
):
    result = IngestionJobService.run_job(db, ctx.tenant_id, ctx.username, job_id)
    if not result["success"] and result.get("message") == "Job introuvable.":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.post("/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    ctx: AuthContext = Depends(require_permissions("connectors:write")),
    db: Session = Depends(get_db),
):
    result = IngestionJobService.retry_job(db, ctx.tenant_id, ctx.username, job_id)
    if not result["success"] and result.get("message") == "Job introuvable.":
        raise HTTPException(status_code=404, detail=result["message"])
    if not result["success"] and result.get("message") == "Limite de retries atteinte.":
        raise HTTPException(status_code=409, detail=result["message"])
    return result

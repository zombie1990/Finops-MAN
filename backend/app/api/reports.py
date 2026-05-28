from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.security import AuthContext, require_permissions
from backend.app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["AI Reports"])


class ReportGenerateRequest(BaseModel):
    report_type: str = Field(..., description="executive|technical|savings|carbon")
    period_days: int = Field(default=30, ge=1, le=365)


@router.get("")
def list_reports(
    ctx: AuthContext = Depends(require_permissions("reports:read")),
    db: Session = Depends(get_db),
):
    return ReportService.list_reports(db, ctx.tenant_id)


@router.post("/generate")
def generate_report(
    request: ReportGenerateRequest,
    ctx: AuthContext = Depends(require_permissions("reports:write")),
    db: Session = Depends(get_db),
):
    try:
        return ReportService.generate_report(
            db=db,
            tenant_id=ctx.tenant_id,
            username=ctx.username,
            report_type=request.report_type,
            period_days=request.period_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{report_id}")
def get_report(
    report_id: str,
    ctx: AuthContext = Depends(require_permissions("reports:read")),
    db: Session = Depends(get_db),
):
    report = ReportService.get_report(db, ctx.tenant_id, report_id)
    if not report.get("id"):
        raise HTTPException(status_code=404, detail=report.get("message", "Rapport introuvable."))
    return report

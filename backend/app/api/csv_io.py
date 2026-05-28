from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.security import AuthContext, require_permissions
from backend.app.services.csv_service import CsvService

router = APIRouter(prefix="/data", tags=["CSV Import / Export"])


class CsvImportRequest(BaseModel):
    column_mapping: Optional[dict] = None


@router.post("/import/preview")
async def preview_csv(
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(require_permissions("connectors:write")),
):
    content = await file.read()
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers CSV sont supportes pour le preview.")
    return CsvService.preview_import(content, file.filename)


@router.post("/import")
async def import_csv(
    file: UploadFile = File(...),
    column_mapping: Optional[str] = Form(default=None),
    ctx: AuthContext = Depends(require_permissions("connectors:write")),
    db: Session = Depends(get_db),
):
    import json

    content = await file.read()
    mapping = json.loads(column_mapping) if column_mapping else None
    result = CsvService.import_costs(
        db=db,
        tenant_id=ctx.tenant_id,
        username=ctx.username,
        file_content=content,
        filename=file.filename,
        column_mapping=mapping,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message") or result.get("errors"))
    return result


@router.get("/import/history")
def import_history(
    ctx: AuthContext = Depends(require_permissions("connectors:read")),
    db: Session = Depends(get_db),
):
    return CsvService.list_import_history(db, ctx.tenant_id)


@router.get("/export/csv")
def export_csv(
    days: int = 30,
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    payload = CsvService.export_costs_csv(db, ctx.tenant_id, days=days)
    return PlainTextResponse(
        content=payload,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="finoptica-costs-{days}d.csv"'},
    )


@router.get("/export/json")
def export_json(
    days: int = 30,
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    from fastapi.responses import JSONResponse

    return JSONResponse(CsvService.export_costs_json(db, ctx.tenant_id, days=days))

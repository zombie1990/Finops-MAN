from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.security import AuthContext, require_permissions
from backend.app.services.platform_service import PlatformService

router = APIRouter(prefix="/platform", tags=["Platform"])


@router.get("/status")
def platform_status(
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    return PlatformService.get_status(db, ctx.tenant_id)

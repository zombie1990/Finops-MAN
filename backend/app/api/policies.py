from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.security import AuthContext, require_permissions
from backend.app.services.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["FinOps Policy-as-Code"])


@router.get("")
def list_policies(
    ctx: AuthContext = Depends(require_permissions("billing:read")),
):
    return PolicyService.list_policies()


@router.post("/evaluate")
def evaluate_policies(
    days: int = Query(30, ge=7, le=90),
    ctx: AuthContext = Depends(require_permissions("billing:read")),
    db: Session = Depends(get_db),
):
    return PolicyService.evaluate_all(db, ctx.tenant_id, days)

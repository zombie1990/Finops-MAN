from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.security import AuthContext, require_permissions
from backend.app.services.github_automation_service import GitHubAutomationService

router = APIRouter(prefix="/automation", tags=["Automation"])


@router.get("/github/status")
def github_status(ctx: AuthContext = Depends(require_permissions("optimization:read"))):
    return {
        "configured": GitHubAutomationService.is_configured(),
        "repo": GitHubAutomationService.is_configured() and __import__(
            "backend.app.config", fromlist=["settings"]
        ).settings.GITHUB_REPO,
    }


@router.post("/github/pr/{recommendation_id}")
def create_github_pr(
    recommendation_id: str,
    ctx: AuthContext = Depends(require_permissions("optimization:write")),
    db: Session = Depends(get_db),
):
    result = GitHubAutomationService.create_remediation_pr(
        db, ctx.tenant_id, ctx.username, recommendation_id
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("message", "Echec PR GitHub"))
    return result

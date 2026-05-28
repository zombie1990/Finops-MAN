import base64
import uuid
from typing import Dict, Optional

import httpx
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import AutomationRun, AuditLog, Recommendation
from datetime import datetime


class GitHubAutomationService:
    @staticmethod
    def is_configured() -> bool:
        return bool(settings.GITHUB_TOKEN and settings.GITHUB_REPO)

    @staticmethod
    def create_remediation_pr(
        db: Session,
        tenant_id: str,
        username: str,
        recommendation_id: str,
    ) -> Dict:
        if not GitHubAutomationService.is_configured():
            return {
                "success": False,
                "message": "GITHUB_TOKEN et GITHUB_REPO requis pour créer une PR.",
            }

        rec = (
            db.query(Recommendation)
            .filter(Recommendation.tenant_id == tenant_id, Recommendation.id == recommendation_id)
            .first()
        )
        if not rec or not rec.remediation_script:
            return {"success": False, "message": "Recommandation ou script introuvable."}

        run_id = str(uuid.uuid4())
        branch = f"finops/{recommendation_id[:12]}"
        repo = settings.GITHUB_REPO
        headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }
        file_path = f"finops/remediations/{recommendation_id}.tf"
        content_b64 = base64.b64encode(rec.remediation_script.encode("utf-8")).decode("utf-8")

        try:
            with httpx.Client(timeout=30.0) as client:
                base_ref = client.get(
                    f"https://api.github.com/repos/{repo}/git/ref/heads/{settings.GITHUB_BASE_BRANCH}",
                    headers=headers,
                )
                base_ref.raise_for_status()
                base_sha = base_ref.json()["object"]["sha"]

                client.post(
                    f"https://api.github.com/repos/{repo}/git/refs",
                    headers=headers,
                    json={"ref": f"refs/heads/{branch}", "sha": base_sha},
                )

                client.put(
                    f"https://api.github.com/repos/{repo}/contents/{file_path}",
                    headers=headers,
                    json={
                        "message": f"FinOps remediation {recommendation_id}",
                        "content": content_b64,
                        "branch": branch,
                    },
                )

                pr = client.post(
                    f"https://api.github.com/repos/{repo}/pulls",
                    headers=headers,
                    json={
                        "title": f"[FinOps] {rec.recommendation_type} - {rec.resource_name}",
                        "head": branch,
                        "base": settings.GITHUB_BASE_BRANCH,
                        "body": (
                            f"## Remédiation FinOps automatique\n\n"
                            f"- Ressource: `{rec.resource_id}`\n"
                            f"- Économie estimée: **{rec.estimated_saving}$/mois**\n"
                            f"- Risque: {rec.operational_risk}\n\n"
                            f"### Rollback\n```\n{rec.rollback_script or 'N/A'}\n```"
                        ),
                    },
                )
                pr.raise_for_status()
                pr_data = pr.json()
                pr_url = pr_data.get("html_url")

            run = AutomationRun(
                id=run_id,
                tenant_id=tenant_id,
                recommendation_id=recommendation_id,
                automation_type="github_pr",
                status="Success",
                pr_url=pr_url,
                details=f"branch={branch}",
                created_at=datetime.utcnow(),
            )
            db.add(run)
            db.add(
                AuditLog(
                    tenant_id=tenant_id,
                    action="github_pr_created",
                    user=username,
                    resource_type="recommendation",
                    resource_id=recommendation_id,
                    details=pr_url,
                    timestamp=datetime.utcnow(),
                )
            )
            db.commit()
            return {"success": True, "run_id": run_id, "pr_url": pr_url, "branch": branch}
        except Exception as exc:
            run = AutomationRun(
                id=run_id,
                tenant_id=tenant_id,
                recommendation_id=recommendation_id,
                status="Failed",
                details=str(exc),
                created_at=datetime.utcnow(),
            )
            db.add(run)
            db.commit()
            return {"success": False, "run_id": run_id, "message": str(exc)}

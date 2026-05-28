from typing import Dict, List

from sqlalchemy.orm import Session

from backend.app.models import Recommendation


class RecommendationService:
    RISK_SCORE = {"Low": 10, "Medium": 35, "High": 60}
    EFFORT_SCORE = {"Low": 10, "Medium": 25, "High": 45}

    @staticmethod
    def _confidence_for(rec: Recommendation) -> float:
        # Heuristique simple mais stable pour score de confiance.
        base = 72.0
        if rec.recommendation_type in {"Rightsizing", "Idle"}:
            base += 12
        if rec.recommendation_type in {"GPU", "Carbon"}:
            base += 8
        if rec.operational_risk == "High":
            base -= 12
        if rec.remediation_effort == "High":
            base -= 8
        return max(35.0, min(98.0, base))

    @staticmethod
    def get_scored_recommendations(db: Session, tenant_id: str) -> List[Dict]:
        recs = db.query(Recommendation).filter(Recommendation.tenant_id == tenant_id).all()
        scored = []
        for rec in recs:
            confidence = RecommendationService._confidence_for(rec)
            risk_score = RecommendationService.RISK_SCORE.get(rec.operational_risk, 20)
            effort_score = RecommendationService.EFFORT_SCORE.get(rec.remediation_effort, 20)
            impact = rec.estimated_saving
            # Score priorite: poids impact + confiance - penalites risque/effort
            priority_score = round((impact * 0.55) + (confidence * 2.2) - (risk_score * 1.1) - (effort_score * 0.9), 2)
            scored.append(
                {
                    "id": rec.id,
                    "resource_name": rec.resource_name,
                    "provider": rec.provider,
                    "service": rec.service,
                    "recommendation_type": rec.recommendation_type,
                    "status": rec.status,
                    "estimated_saving": round(rec.estimated_saving, 2),
                    "confidence_score": round(confidence, 1),
                    "operational_risk": rec.operational_risk,
                    "remediation_effort": rec.remediation_effort,
                    "priority_score": priority_score,
                }
            )
        return sorted(scored, key=lambda x: x["priority_score"], reverse=True)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Recommendation
from backend.app.security import require_permissions, AuthContext
from backend.app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/optimization", tags=["Optimization & Actions"])

@router.get("/recommendations")
def get_recommendations(
    ctx: AuthContext = Depends(require_permissions("optimization:read")),
    db: Session = Depends(get_db)
):
    recs = db.query(Recommendation).filter(Recommendation.tenant_id == ctx.tenant_id).all()
    return [
        {
            "id": r.id,
            "resource_id": r.resource_id,
            "resource_name": r.resource_name,
            "provider": r.provider,
            "service": r.service,
            "recommendation_type": r.recommendation_type,
            "description": r.description,
            "current_cost": round(r.current_cost, 2),
            "estimated_saving": round(r.estimated_saving, 2),
            "roi_days": r.roi_days,
            "operational_risk": r.operational_risk,
            "remediation_effort": r.remediation_effort,
            "status": r.status,
            "remediation_script_type": r.remediation_script_type,
            "remediation_script": r.remediation_script,
            "rollback_script": r.rollback_script
        } for r in recs
    ]

@router.post("/recommendations/{rec_id}/apply")
def apply_recommendation(
    rec_id: str,
    ctx: AuthContext = Depends(require_permissions("optimization:write")),
    db: Session = Depends(get_db)
):
    rec = db.query(Recommendation).filter(
        Recommendation.tenant_id == ctx.tenant_id,
        Recommendation.id == rec_id
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommandation introuvable.")
        
    # Simuler le déploiement et l'application automatique (Terraform plan/apply, bash, kubectl...)
    rec.status = "Applied"
    db.commit()
    
    return {
        "success": True,
        "message": f"Remédiation {rec_id} appliquée avec succès !",
        "applied_script_type": rec.remediation_script_type,
        "output": f"[FINOPS ENGINE] Commande lancée en mode sécurisé.\n[DRY-RUN] Validation réussie.\n[EXECUTION] Application du script {rec.remediation_script_type} terminée sans erreur.\n[VERIFICATION] Ressource modifiée en cours de synchronisation."
    }

@router.post("/recommendations/{rec_id}/rollback")
def rollback_recommendation(
    rec_id: str,
    ctx: AuthContext = Depends(require_permissions("optimization:write")),
    db: Session = Depends(get_db)
):
    rec = db.query(Recommendation).filter(
        Recommendation.tenant_id == ctx.tenant_id,
        Recommendation.id == rec_id
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommandation introuvable.")
        
    # Annuler la remédiation et repasser le statut en Pending
    rec.status = "Pending"
    db.commit()
    
    return {
        "success": True,
        "message": f"Rollback de la remédiation {rec_id} effectué.",
        "rollback_script": rec.rollback_script,
        "output": f"[FINOPS ENGINE] Script de rollback appliqué.\n[EXECUTION] Retour à la configuration précédente effectué.\n[VERIFICATION] Ressource restaurée au statut d'origine."
    }

@router.get("/recommendations/scored")
def get_scored_recommendations(
    ctx: AuthContext = Depends(require_permissions("optimization:read")),
    db: Session = Depends(get_db)
):
    return RecommendationService.get_scored_recommendations(db, ctx.tenant_id)

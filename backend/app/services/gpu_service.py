"""Analytics GPU / IA workloads (OpenAI, SageMaker, GPU instances)."""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import CostItem
from backend.app.services.finops_engine import GPU_SERVICE_KEYWORDS


class GpuService:
    @staticmethod
    def _is_gpu_service(service: str) -> bool:
        s = service.lower()
        return any(k in s for k in GPU_SERVICE_KEYWORDS)

    @staticmethod
    def get_gpu_workload_analytics(db: Session, tenant_id: str, days: int = 30) -> Dict:
        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            db.query(
                CostItem.provider,
                CostItem.service,
                func.sum(CostItem.cost).label("cost"),
                func.sum(CostItem.usage_quantity).label("usage"),
            )
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= since)
            .group_by(CostItem.provider, CostItem.service)
            .all()
        )

        workloads: List[Dict] = []
        total_gpu_cost = 0.0
        by_provider: Dict[str, float] = defaultdict(float)

        for r in rows:
            if not GpuService._is_gpu_service(r.service):
                continue
            cost = float(r.cost or 0)
            total_gpu_cost += cost
            by_provider[r.provider] += cost
            unit_cost = cost / float(r.usage or 1) if r.usage else cost
            workloads.append(
                {
                    "provider": r.provider,
                    "service": r.service,
                    "cost": round(cost, 2),
                    "usage_quantity": round(float(r.usage or 0), 2),
                    "unit_cost": round(unit_cost, 4),
                    "optimization_hint": (
                        "Envisager modèle plus léger ou batching"
                        if "gpt" in r.service.lower()
                        else "Rightsizing GPU / spot instances"
                    ),
                }
            )

        workloads.sort(key=lambda x: x["cost"], reverse=True)
        return {
            "days": days,
            "total_gpu_ai_cost": round(total_gpu_cost, 2),
            "share_of_cloud_pct": None,
            "by_provider": {k: round(v, 2) for k, v in by_provider.items()},
            "workloads": workloads[:25],
            "recommendations": [
                "Activer le cache des inférences pour réduire les tokens",
                "Utiliser des instances GPU spot pour les jobs batch",
                "Monitorer coût par 1M tokens / heure GPU",
            ],
        }

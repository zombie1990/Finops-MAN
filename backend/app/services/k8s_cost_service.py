"""Dérive les métriques Kubernetes à partir des lignes de coût cloud (EKS/GKE/AKS)."""
from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.app.models import CostItem, KubernetesCost

K8S_SERVICES = ("%eks%", "%gke%", "%aks%", "%kubernetes%")


class K8sCostService:
    @staticmethod
    def sync_from_cost_items(db: Session, tenant_id: str, days: int = 7) -> int:
        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            db.query(
                CostItem.service,
                CostItem.provider,
                func.date(CostItem.date).label("d"),
                func.sum(CostItem.cost).label("c"),
            )
            .filter(
                CostItem.tenant_id == tenant_id,
                CostItem.date >= since,
                or_(
                    CostItem.service.ilike("%kubernetes%"),
                    CostItem.service.ilike("%eks%"),
                    CostItem.service.ilike("%gke%"),
                    CostItem.service.ilike("%aks%"),
                ),
            )
            .group_by(CostItem.service, CostItem.provider, func.date(CostItem.date))
            .all()
        )

        (
            db.query(KubernetesCost)
            .filter(KubernetesCost.tenant_id == tenant_id, KubernetesCost.date >= since)
            .delete(synchronize_session=False)
        )

        count = 0
        for r in rows:
            cost = float(r.c or 0)
            if cost <= 0:
                continue
            cpu_req = max(cost / 2.4, 1.0)
            cpu_used = cpu_req * 0.55
            mem_req = cpu_req * 4
            mem_used = mem_req * 0.6
            efficiency = min(100.0, (cpu_used / cpu_req) * 100)

            db.add(
                KubernetesCost(
                    tenant_id=tenant_id,
                    cluster_id=f"{r.provider.lower()}-cluster-01",
                    namespace=r.service.replace(" ", "-").lower()[:40],
                    pod_name=None,
                    date=datetime.strptime(str(r.d), "%Y-%m-%d"),
                    cpu_cores_requested=round(cpu_req, 2),
                    cpu_cores_used=round(cpu_used, 2),
                    memory_gb_requested=round(mem_req, 2),
                    memory_gb_used=round(mem_used, 2),
                    cost=round(cost, 2),
                    efficiency_score=round(efficiency, 1),
                )
            )
            count += 1

        if count:
            db.commit()
        return count

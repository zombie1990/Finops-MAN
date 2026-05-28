"""
Showback / chargeback par dimensions (équipe, environnement, cost center).
Utilise les tags JSON sur CostItem (FinOps Foundation — Allocation).
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy.orm import Session

from backend.app.models import CostItem

ALLOCATION_DIMENSIONS = ("team", "env", "cost_center", "product", "owner")


class AllocationService:
    @staticmethod
    def get_allocation(
        db: Session,
        tenant_id: str,
        days: int = 30,
        group_by: str = "team",
    ) -> Dict:
        if group_by not in ALLOCATION_DIMENSIONS:
            group_by = "team"

        today = datetime.utcnow().date()
        start = datetime.combine(today - timedelta(days=days), datetime.min.time())

        items = (
            db.query(CostItem.cost, CostItem.carbon_emissions, CostItem.tags, CostItem.provider)
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= start)
            .all()
        )

        buckets: Dict[str, Dict] = defaultdict(
            lambda: {"cost": 0.0, "carbon_kg": 0.0, "providers": defaultdict(float)}
        )

        for item in items:
            tags = item.tags if isinstance(item.tags, dict) else {}
            label = tags.get(group_by) or tags.get("cost_center") if group_by == "team" else None
            if not label:
                label = tags.get(group_by)
            label = str(label) if label else "unallocated"

            buckets[label]["cost"] += float(item.cost or 0)
            buckets[label]["carbon_kg"] += float(item.carbon_emissions or 0)
            buckets[label]["providers"][item.provider] += float(item.cost or 0)

        total_cost = sum(b["cost"] for b in buckets.values()) or 1.0
        rows: List[Dict] = []
        for name, data in sorted(buckets.items(), key=lambda x: x[1]["cost"], reverse=True):
            rows.append(
                {
                    "dimension": group_by,
                    "label": name,
                    "cost": round(data["cost"], 2),
                    "carbon_kg": round(data["carbon_kg"], 2),
                    "share_pct": round(data["cost"] / total_cost * 100, 1),
                    "by_provider": {
                        p: round(c, 2) for p, c in sorted(data["providers"].items(), key=lambda x: -x[1])
                    },
                }
            )

        return {
            "group_by": group_by,
            "days": days,
            "total_cost": round(total_cost, 2),
            "dimensions_available": list(ALLOCATION_DIMENSIONS),
            "allocations": rows,
        }

    @staticmethod
    def get_chargeback_summary(db: Session, tenant_id: str, days: int = 30) -> Dict:
        """Vue showback multi-dimensions pour dashboards enterprise."""
        summary = {}
        for dim in ("team", "env", "cost_center"):
            summary[dim] = AllocationService.get_allocation(db, tenant_id, days, dim)["allocations"][:10]
        return {"days": days, "showback": summary}

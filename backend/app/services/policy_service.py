"""
Policy-as-code FinOps : règles déclaratives évaluées sur les données de coût.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import CostItem, Recommendation


DEFAULT_POLICIES: List[Dict[str, Any]] = [
    {
        "id": "finops-001",
        "name": "Tag environnement obligatoire",
        "category": "governance",
        "severity": "High",
        "description": "Au moins 90% des coûts doivent avoir le tag env.",
        "rule_type": "tag_coverage",
        "params": {"tag_key": "env", "min_coverage_pct": 90},
    },
    {
        "id": "finops-002",
        "name": "Tag cost_center pour chargeback",
        "category": "allocation",
        "severity": "Medium",
        "description": "70% des dépenses doivent être rattachées à un cost center.",
        "rule_type": "tag_coverage",
        "params": {"tag_key": "cost_center", "min_coverage_pct": 70},
    },
    {
        "id": "finops-003",
        "name": "Pas de ressources dev > 500 USD/mois",
        "category": "cost_control",
        "severity": "High",
        "description": "Environnement dev ne doit pas dépasser 500 USD sur 30j.",
        "rule_type": "env_spend_cap",
        "params": {"env": "dev", "max_spend": 500},
    },
    {
        "id": "finops-004",
        "name": "Recommandations critiques non traitées",
        "category": "optimization",
        "severity": "Critical",
        "description": "Moins de 5 recommandations High risk en attente.",
        "rule_type": "pending_high_risk_recs",
        "params": {"max_pending": 5},
    },
    {
        "id": "finops-005",
        "name": "GreenOps — intensité carbone",
        "category": "sustainability",
        "severity": "Low",
        "description": "Alerte si carbone > 0.12 kg CO2 par dollar dépensé.",
        "rule_type": "carbon_intensity",
        "params": {"max_kg_per_dollar": 0.12},
    },
]


class PolicyService:
    @staticmethod
    def list_policies() -> List[Dict]:
        return DEFAULT_POLICIES

    @staticmethod
    def _tag_coverage(db: Session, tenant_id: str, days: int, tag_key: str) -> float:
        since = datetime.utcnow() - timedelta(days=days)
        items = (
            db.query(CostItem.cost, CostItem.tags)
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= since)
            .all()
        )
        if not items:
            return 100.0
        total = sum(float(i.cost or 0) for i in items)
        tagged = 0.0
        for i in items:
            tags = i.tags if isinstance(i.tags, dict) else {}
            if tags.get(tag_key):
                tagged += float(i.cost or 0)
        return (tagged / total * 100) if total > 0 else 100.0

    @staticmethod
    def evaluate_all(db: Session, tenant_id: str, days: int = 30) -> Dict:
        results = []
        passed = 0
        failed = 0

        for policy in DEFAULT_POLICIES:
            ptype = policy["rule_type"]
            params = policy.get("params", {})
            compliant = True
            actual = None
            expected = None

            if ptype == "tag_coverage":
                actual = round(PolicyService._tag_coverage(db, tenant_id, days, params["tag_key"]), 1)
                expected = params["min_coverage_pct"]
                compliant = actual >= expected

            elif ptype == "env_spend_cap":
                since = datetime.utcnow() - timedelta(days=days)
                spend = (
                    db.query(func.sum(CostItem.cost))
                    .filter(CostItem.tenant_id == tenant_id, CostItem.date >= since)
                    .scalar()
                    or 0
                )
                items = db.query(CostItem.cost, CostItem.tags).filter(
                    CostItem.tenant_id == tenant_id, CostItem.date >= since
                ).all()
                dev_spend = 0.0
                for i in items:
                    tags = i.tags if isinstance(i.tags, dict) else {}
                    if tags.get("env") == params["env"]:
                        dev_spend += float(i.cost or 0)
                actual = round(dev_spend, 2)
                expected = params["max_spend"]
                compliant = actual <= expected

            elif ptype == "pending_high_risk_recs":
                count = (
                    db.query(Recommendation)
                    .filter(
                        Recommendation.tenant_id == tenant_id,
                        Recommendation.status == "Pending",
                        Recommendation.operational_risk == "High",
                    )
                    .count()
                )
                actual = count
                expected = params["max_pending"]
                compliant = count <= expected

            elif ptype == "carbon_intensity":
                since = datetime.utcnow() - timedelta(days=days)
                cost = float(
                    db.query(func.sum(CostItem.cost))
                    .filter(CostItem.tenant_id == tenant_id, CostItem.date >= since)
                    .scalar()
                    or 0
                )
                carbon = float(
                    db.query(func.sum(CostItem.carbon_emissions))
                    .filter(CostItem.tenant_id == tenant_id, CostItem.date >= since)
                    .scalar()
                    or 0
                )
                actual = round(carbon / cost, 4) if cost > 0 else 0
                expected = params["max_kg_per_dollar"]
                compliant = actual <= expected

            if compliant:
                passed += 1
            else:
                failed += 1

            results.append(
                {
                    **policy,
                    "compliant": compliant,
                    "actual_value": actual,
                    "expected_value": expected,
                    "evaluated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                }
            )

        score = round(passed / len(results) * 100, 1) if results else 100.0
        return {
            "compliance_score": score,
            "passed": passed,
            "failed": failed,
            "total_policies": len(results),
            "policies": results,
        }

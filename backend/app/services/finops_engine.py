"""
Moteur FinOps enterprise : détection d'anomalies sur données réelles,
génération de recommandations (rightsizing, savings plans, idle).
"""
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.app.models import Anomaly, CostItem, Recommendation


COMPUTE_SERVICE_KEYWORDS = (
    "ec2",
    "compute",
    "virtual machine",
    "kubernetes",
    "eks",
    "gke",
    "aks",
    "container",
)
GPU_SERVICE_KEYWORDS = ("gpu", "sagemaker", "machine learning", "inference", "openai", "gpt")


class FinOpsEngine:
    @staticmethod
    def _period_start(days: int) -> datetime:
        today = datetime.utcnow().date()
        return datetime.combine(today - timedelta(days=days), datetime.min.time())

    @staticmethod
    def _severity_from_deviation(pct: float) -> str:
        if pct >= 200:
            return "Critical"
        if pct >= 100:
            return "High"
        if pct >= 50:
            return "Medium"
        return "Low"

    @staticmethod
    def _anomaly_id(tenant_id: str, provider: str, service: str, date_str: str) -> str:
        raw = f"{tenant_id}:{provider}:{service}:{date_str}"
        return "anom-" + hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def detect_anomalies_from_costs(
        db: Session,
        tenant_id: str,
        lookback_days: int = 30,
        z_threshold: float = 2.0,
    ) -> int:
        """Détection statistique (z-score) sur coûts journaliers par provider/service."""
        start = FinOpsEngine._period_start(lookback_days)
        rows = (
            db.query(
                func.date(CostItem.date).label("cost_date"),
                CostItem.provider,
                CostItem.service,
                func.sum(CostItem.cost).label("daily_cost"),
            )
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= start)
            .group_by(func.date(CostItem.date), CostItem.provider, CostItem.service)
            .all()
        )
        if not rows:
            return 0

        series: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(dict)
        for r in rows:
            key = (r.provider, r.service)
            series[key][str(r.cost_date)] = float(r.daily_cost or 0)

        created = 0
        today_str = str(datetime.utcnow().date())

        for (provider, service), daily in series.items():
            if len(daily) < 5:
                continue
            sorted_dates = sorted(daily.keys())
            latest_date = sorted_dates[-1]
            history = [daily[d] for d in sorted_dates[:-1]]
            if not history:
                continue
            mean = sum(history) / len(history)
            if mean <= 0:
                continue
            variance = sum((x - mean) ** 2 for x in history) / len(history)
            std = variance ** 0.5
            actual = daily[latest_date]
            deviation_pct = ((actual - mean) / mean) * 100.0
            z = (actual - mean) / std if std > 0 else (10.0 if actual > mean * 1.5 else 0)

            if actual <= mean * 1.25:
                continue
            if std > 0 and z < z_threshold and deviation_pct < 50:
                continue

            anom_id = FinOpsEngine._anomaly_id(tenant_id, provider, service, latest_date)
            existing = db.query(Anomaly).filter(Anomaly.id == anom_id).first()
            if existing:
                continue

            severity = FinOpsEngine._severity_from_deviation(deviation_pct)
            db.add(
                Anomaly(
                    id=anom_id,
                    tenant_id=tenant_id,
                    date=datetime.strptime(latest_date, "%Y-%m-%d"),
                    provider=provider,
                    service=service,
                    resource_id=f"{provider.lower()}-{service.lower().replace(' ', '-')}",
                    expected_cost=round(mean, 2),
                    actual_cost=round(actual, 2),
                    deviation_percentage=round(deviation_pct, 1),
                    severity=severity,
                    status="Unresolved",
                    description=(
                        f"Pic de coût détecté sur {service} ({provider}). "
                        f"Coût journalier {actual:.2f} $ vs moyenne {mean:.2f} $ "
                        f"(écart {deviation_pct:.0f}%, z≈{z:.1f})."
                    ),
                )
            )
            created += 1

        if created:
            db.commit()
        return created

    @staticmethod
    def _is_compute_service(service: str) -> bool:
        s = service.lower()
        return any(k in s for k in COMPUTE_SERVICE_KEYWORDS)

    @staticmethod
    def generate_rightsizing_recommendations(
        db: Session,
        tenant_id: str,
        days: int = 30,
        min_monthly_cost: float = 150.0,
    ) -> int:
        start = FinOpsEngine._period_start(days)
        rows = (
            db.query(
                CostItem.resource_id,
                CostItem.resource_name,
                CostItem.provider,
                CostItem.service,
                func.sum(CostItem.cost).label("total_cost"),
                func.avg(CostItem.usage_quantity).label("avg_usage"),
            )
            .filter(
                CostItem.tenant_id == tenant_id,
                CostItem.date >= start,
                CostItem.resource_id.isnot(None),
            )
            .group_by(
                CostItem.resource_id,
                CostItem.resource_name,
                CostItem.provider,
                CostItem.service,
            )
            .all()
        )

        created = 0
        for r in rows:
            if not FinOpsEngine._is_compute_service(r.service):
                continue
            total = float(r.total_cost or 0)
            if total < min_monthly_cost:
                continue
            avg_usage = float(r.avg_usage or 0)
            # Heuristique FinOps : faible usage relatif au coût → rightsizing
            usage_ratio = avg_usage / max(total, 1.0)
            if usage_ratio > 0.5 and total < min_monthly_cost * 3:
                continue

            rec_id = f"rec-rs-{hashlib.sha256((tenant_id + r.resource_id).encode()).hexdigest()[:12]}"
            if db.query(Recommendation).filter(Recommendation.id == rec_id).first():
                continue

            saving = round(total * 0.35, 2)
            db.add(
                Recommendation(
                    id=rec_id,
                    tenant_id=tenant_id,
                    resource_id=r.resource_id,
                    resource_name=r.resource_name or r.resource_id,
                    provider=r.provider,
                    service=r.service,
                    recommendation_type="Rightsizing",
                    description=(
                        f"Rightsizing recommandé : coût {total:.0f} $ sur {days}j "
                        f"avec utilisation faible (ratio {usage_ratio:.2f}). "
                        "Réduire la taille d'instance ou passer en famille cost-optimized."
                    ),
                    current_cost=round(total, 2),
                    estimated_saving=saving,
                    roi_days=21,
                    operational_risk="Low",
                    remediation_effort="Medium",
                    status="Pending",
                    remediation_script_type="terraform",
                    remediation_script="# terraform plan -target=module.rightsizing",
                    rollback_script="# terraform apply rollback state",
                )
            )
            created += 1

        if created:
            db.commit()
        return created

    @staticmethod
    def generate_savings_plan_recommendations(
        db: Session,
        tenant_id: str,
        days: int = 30,
        min_compute_spend: float = 2000.0,
    ) -> int:
        start = FinOpsEngine._period_start(days)
        compute_spend = 0.0
        by_provider: Dict[str, float] = defaultdict(float)

        rows = (
            db.query(CostItem.provider, CostItem.service, func.sum(CostItem.cost).label("c"))
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= start)
            .group_by(CostItem.provider, CostItem.service)
            .all()
        )
        for r in rows:
            if not FinOpsEngine._is_compute_service(r.service):
                continue
            c = float(r.c or 0)
            compute_spend += c
            by_provider[r.provider] += c

        if compute_spend < min_compute_spend:
            return 0

        rec_id = f"rec-sp-{tenant_id[:8]}"
        if db.query(Recommendation).filter(Recommendation.id == rec_id).first():
            return 0

        top_provider = max(by_provider.items(), key=lambda x: x[1])[0] if by_provider else "AWS"
        saving = round(compute_spend * 0.28, 2)

        db.add(
            Recommendation(
                id=rec_id,
                tenant_id=tenant_id,
                resource_id=f"{top_provider.lower()}-compute-commitment",
                resource_name=f"{top_provider} Compute Commitment",
                provider=top_provider,
                service="Compute (aggregated)",
                recommendation_type="SavingsPlan",
                description=(
                    f"Dépenses compute {compute_spend:.0f} $ sur {days}j. "
                    "Envisager Savings Plans / Reserved Instances / CUD selon le cloud "
                    f"(pic sur {top_provider})."
                ),
                current_cost=round(compute_spend, 2),
                estimated_saving=saving,
                roi_days=45,
                operational_risk="Medium",
                remediation_effort="High",
                status="Pending",
                remediation_script_type="aws_cli",
                remediation_script="# aws ce get-savings-plans-purchase-recommendation",
            )
        )
        db.commit()
        return 1

    @staticmethod
    def generate_spot_preemptible_hints(db: Session, tenant_id: str, days: int = 30) -> int:
        start = FinOpsEngine._period_start(days)
        rows = (
            db.query(CostItem.provider, func.sum(CostItem.cost).label("c"))
            .filter(
                CostItem.tenant_id == tenant_id,
                CostItem.date >= start,
                or_(
                    CostItem.service.ilike("%kubernetes%"),
                    CostItem.service.ilike("%eks%"),
                    CostItem.service.ilike("%gke%"),
                    CostItem.service.ilike("%aks%"),
                ),
            )
            .group_by(CostItem.provider)
            .all()
        )
        created = 0
        for r in rows:
            total = float(r.c or 0)
            if total < 500:
                continue
            rec_id = f"rec-spot-{r.provider.lower()}"
            if db.query(Recommendation).filter(Recommendation.id == rec_id).first():
                continue
            db.add(
                Recommendation(
                    id=rec_id,
                    tenant_id=tenant_id,
                    resource_id=f"{r.provider.lower()}-k8s-workloads",
                    resource_name=f"{r.provider} K8s Spot",
                    provider=r.provider,
                    service="Kubernetes",
                    recommendation_type="Spot",
                    description=(
                        f"Coût K8s {total:.0f} $ — workloads fault-tolerant candidats "
                        "Spot / Preemptible (CAST AI style autoscaling)."
                    ),
                    current_cost=round(total, 2),
                    estimated_saving=round(total * 0.55, 2),
                    roi_days=14,
                    operational_risk="Medium",
                    remediation_effort="Medium",
                    status="Pending",
                    remediation_script_type="kubectl",
                    remediation_script="# kubectl label nodes workload=spot-candidate",
                )
            )
            created += 1
        if created:
            db.commit()
        return created

    @staticmethod
    def generate_gpu_optimization_hints(db: Session, tenant_id: str, days: int = 30) -> int:
        from backend.app.services.gpu_service import GpuService

        analytics = GpuService.get_gpu_workload_analytics(db, tenant_id, days)
        if analytics["total_gpu_ai_cost"] < 100:
            return 0
        rec_id = f"rec-gpu-{tenant_id[:8]}"
        if db.query(Recommendation).filter(Recommendation.id == rec_id).first():
            return 0
        db.add(
            Recommendation(
                id=rec_id,
                tenant_id=tenant_id,
                resource_id="gpu-ai-workloads",
                resource_name="GPU / IA Workloads",
                provider="Multi",
                service="GPU & AI",
                recommendation_type="GPU",
                description=(
                    f"Dépenses GPU/IA: {analytics['total_gpu_ai_cost']:.0f} $. "
                    "Optimiser modèles, batching et instances spot GPU."
                ),
                current_cost=analytics["total_gpu_ai_cost"],
                estimated_saving=round(analytics["total_gpu_ai_cost"] * 0.25, 2),
                roi_days=30,
                operational_risk="Low",
                remediation_effort="Medium",
                status="Pending",
                remediation_script_type="bash",
                remediation_script="# finops: review gpu workload quotas",
            )
        )
        db.commit()
        return 1

    @staticmethod
    def run_full_analysis(db: Session, tenant_id: str) -> Dict[str, int]:
        from backend.app.services.alert_service import AlertService
        from backend.app.services.k8s_cost_service import K8sCostService
        from backend.app.services.policy_service import PolicyService

        PolicyService.evaluate_all(db, tenant_id)
        k8s_synced = K8sCostService.sync_from_cost_items(db, tenant_id)
        alerts_fired = AlertService.evaluate_and_fire(db, tenant_id)

        return {
            "anomalies_detected": FinOpsEngine.detect_anomalies_from_costs(db, tenant_id),
            "rightsizing_created": FinOpsEngine.generate_rightsizing_recommendations(db, tenant_id),
            "savings_plans_created": FinOpsEngine.generate_savings_plan_recommendations(db, tenant_id),
            "spot_hints_created": FinOpsEngine.generate_spot_preemptible_hints(db, tenant_id),
            "gpu_hints_created": FinOpsEngine.generate_gpu_optimization_hints(db, tenant_id),
            "k8s_rows_synced": k8s_synced,
            "alerts_fired": alerts_fired,
        }

import uuid
from calendar import monthrange
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import AuditLog, Budget, CostItem


class BudgetService:
    @staticmethod
    def _month_bounds() -> tuple:
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)
        last_day = monthrange(now.year, now.month)[1]
        end = datetime(now.year, now.month, last_day, 23, 59, 59)
        return start, end, last_day

    @staticmethod
    def _query_spent(
        db: Session,
        tenant_id: str,
        start: datetime,
        end: datetime,
        provider_filter: Optional[str] = None,
        service_filter: Optional[str] = None,
    ) -> float:
        q = db.query(func.sum(CostItem.cost)).filter(
            CostItem.tenant_id == tenant_id,
            CostItem.date >= start,
            CostItem.date <= end,
        )
        if provider_filter and provider_filter.lower() != "all":
            q = q.filter(CostItem.provider == provider_filter)
        if service_filter:
            q = q.filter(CostItem.service.ilike(f"%{service_filter}%"))
        return float(q.scalar() or 0.0)

    @staticmethod
    def refresh_budget_metrics(db: Session, budget: Budget) -> Budget:
        start, end, days_in_month = BudgetService._month_bounds()
        now = datetime.utcnow()
        elapsed_days = max((now.date() - start.date()).days + 1, 1)

        spent = BudgetService._query_spent(
            db,
            budget.tenant_id,
            start,
            now,
            budget.provider_filter,
            budget.service_filter,
        )
        budget.spent = round(spent, 2)

        daily_run_rate = spent / elapsed_days
        budget.forecast = round(daily_run_rate * days_in_month, 2)

        pct = (budget.forecast / budget.amount * 100) if budget.amount > 0 else 0
        if pct >= 100:
            budget.status = "Exceeded"
        elif pct >= budget.alert_threshold_critical:
            budget.status = "Critical"
        elif pct >= budget.alert_threshold_warning:
            budget.status = "Warning"
        else:
            budget.status = "On Track"

        budget.updated_at = datetime.utcnow()
        return budget

    @staticmethod
    def list_budgets(db: Session, tenant_id: str) -> List[Dict]:
        budgets = db.query(Budget).filter(Budget.tenant_id == tenant_id).order_by(Budget.created_at.desc()).all()
        if not budgets:
            default = BudgetService.create_budget(
                db,
                tenant_id,
                username="system",
                name="Budget Cloud Mensuel",
                amount=50000.0,
                period="monthly",
                provider_filter="All",
            )
            budgets = [default]

        result = []
        for b in budgets:
            BudgetService.refresh_budget_metrics(db, b)
            result.append(BudgetService._serialize(b))
        db.commit()
        return result

    @staticmethod
    def _serialize(b: Budget) -> Dict:
        utilization = round((b.spent / b.amount * 100), 1) if b.amount > 0 else 0
        forecast_pct = round((b.forecast / b.amount * 100), 1) if b.amount > 0 else 0
        return {
            "id": b.id,
            "name": b.name,
            "amount": round(b.amount, 2),
            "period": b.period,
            "provider_filter": b.provider_filter,
            "service_filter": b.service_filter,
            "spent": b.spent,
            "forecast": b.forecast,
            "status": b.status,
            "utilization_pct": utilization,
            "forecast_pct": forecast_pct,
            "alert_threshold_warning": b.alert_threshold_warning,
            "alert_threshold_critical": b.alert_threshold_critical,
            "updated_at": b.updated_at.strftime("%Y-%m-%d %H:%M") if b.updated_at else None,
        }

    @staticmethod
    def create_budget(
        db: Session,
        tenant_id: str,
        username: str,
        name: str,
        amount: float,
        period: str = "monthly",
        provider_filter: Optional[str] = "All",
        service_filter: Optional[str] = None,
        alert_threshold_warning: float = 75.0,
        alert_threshold_critical: float = 90.0,
    ) -> Budget:
        budget = Budget(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            amount=amount,
            period=period,
            provider_filter=provider_filter,
            service_filter=service_filter,
            alert_threshold_warning=alert_threshold_warning,
            alert_threshold_critical=alert_threshold_critical,
        )
        db.add(budget)
        BudgetService.refresh_budget_metrics(db, budget)
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                action="budget_created",
                user=username,
                resource_type="budget",
                resource_id=budget.id,
                details=name,
                timestamp=datetime.utcnow(),
            )
        )
        db.commit()
        db.refresh(budget)
        return budget

    @staticmethod
    def get_forecast(db: Session, tenant_id: str, days: int = 30) -> Dict:
        """Prévision linéaire + run-rate (FinOps Foundation — Forecast capability)."""
        today = datetime.utcnow().date()
        start = datetime.combine(today - timedelta(days=days), datetime.min.time())

        daily_rows = (
            db.query(func.date(CostItem.date).label("d"), func.sum(CostItem.cost).label("c"))
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= start)
            .group_by(func.date(CostItem.date))
            .order_by("d")
            .all()
        )

        points = [{"date": str(r.d), "cost": round(float(r.c or 0), 2)} for r in daily_rows]
        totals = [p["cost"] for p in points]

        if len(totals) < 2:
            run_rate = totals[0] if totals else 0.0
            projection = run_rate * days
            return {
                "days_analyzed": days,
                "historical": points,
                "daily_run_rate": round(run_rate, 2),
                "period_projection": round(projection, 2),
                "month_end_projection": round(run_rate * 30, 2),
                "trend_pct": 0.0,
                "method": "run_rate",
            }

        n = len(totals)
        x_mean = (n - 1) / 2.0
        y_mean = sum(totals) / n
        num = sum((i - x_mean) * (totals[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n)) or 1.0
        slope = num / den
        intercept = y_mean - slope * x_mean

        future_days = 7
        forecast_points = []
        for i in range(future_days):
            idx = n + i
            projected = max(intercept + slope * idx, 0)
            future_date = today + timedelta(days=i + 1)
            forecast_points.append(
                {"date": str(future_date), "cost": round(projected, 2), "projected": True}
            )

        run_rate = sum(totals[-7:]) / min(7, len(totals))
        month_end = run_rate * 30
        trend_pct = ((totals[-1] - totals[0]) / totals[0] * 100) if totals[0] > 0 else 0

        return {
            "days_analyzed": days,
            "historical": points,
            "forecast": forecast_points,
            "daily_run_rate": round(run_rate, 2),
            "period_projection": round(intercept + slope * (n + days), 2),
            "month_end_projection": round(month_end, 2),
            "trend_pct": round(trend_pct, 2),
            "method": "linear_regression",
        }

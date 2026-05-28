import csv
import io
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.models import AuditLog, CostItem, ScanResult, Tenant


REQUIRED_COST_COLUMNS = {"date", "provider", "service", "cost"}
OPTIONAL_COST_COLUMNS = {
    "account_id",
    "resource_id",
    "resource_name",
    "region",
    "usage_quantity",
    "usage_unit",
    "team",
    "env",
    "cost_center",
    "product",
}


class CsvService:
    @staticmethod
    def preview_import(file_content: bytes, filename: str) -> Dict[str, Any]:
        text = file_content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        headers = [h.strip() for h in (reader.fieldnames or [])]
        rows = list(reader)[:20]
        mapped_ok = REQUIRED_COST_COLUMNS.issubset({h.lower().strip() for h in headers})
        return {
            "filename": filename,
            "headers": headers,
            "preview_rows": rows,
            "required_columns": sorted(REQUIRED_COST_COLUMNS),
            "optional_columns": sorted(OPTIONAL_COST_COLUMNS),
            "validation_ok": mapped_ok,
            "row_count_preview": len(rows),
        }

    @staticmethod
    def import_costs(
        db: Session,
        tenant_id: str,
        username: str,
        file_content: bytes,
        filename: str,
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not db.query(Tenant).filter(Tenant.id == tenant_id).first():
            db.add(Tenant(id=tenant_id, name="Default Tenant", created_at=datetime.utcnow()))
            db.commit()

        scan_id = str(uuid.uuid4())
        scan = ScanResult(
            id=scan_id,
            tenant_id=tenant_id,
            filename=filename,
            file_type="csv",
            status="Processing",
            uploaded_at=datetime.utcnow(),
        )
        db.add(scan)
        db.commit()

        try:
            text = file_content.decode("utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            mapping = {k.lower(): v for k, v in (column_mapping or {}).items()}
            items = 0
            total_cost = 0.0
            providers = set()
            errors = []

            for idx, row in enumerate(reader, start=2):
                try:
                    row_norm = {k.lower().strip(): v for k, v in row.items()}

                    def col(name: str) -> str:
                        source = mapping.get(name, name).lower().strip()
                        return (row_norm.get(source) or row_norm.get(name) or "").strip()

                    date_raw = col("date")
                    provider = col("provider")
                    service = col("service")
                    cost_raw = col("cost")
                    if not date_raw or not provider or not service or not cost_raw:
                        raise ValueError("Colonnes obligatoires manquantes")

                    day = datetime.fromisoformat(date_raw.replace("Z", ""))
                    cost_val = float(cost_raw.replace(",", "."))
                    account_id = col("account_id") or f"csv-{provider.lower()}"
                    providers.add(provider)

                    db.add(
                        CostItem(
                            tenant_id=tenant_id,
                            account_id=account_id,
                            date=day,
                            provider=provider,
                            service=service,
                            resource_id=col("resource_id") or None,
                            resource_name=col("resource_name") or None,
                            region=col("region") or None,
                            cost=cost_val,
                            usage_quantity=float(col("usage_quantity") or 0) if col("usage_quantity") else 0.0,
                            usage_unit=col("usage_unit") or None,
                            tags={
                                "source": "csv_import",
                                "filename": filename,
                                **{
                                    k: col(k)
                                    for k in ("team", "env", "cost_center", "product")
                                    if col(k)
                                },
                            },
                            carbon_emissions=round(cost_val * 0.08, 4),
                        )
                    )
                    items += 1
                    total_cost += cost_val
                except Exception as row_exc:
                    errors.append(f"Ligne {idx}: {row_exc}")

            scan.status = "Completed" if items > 0 else "Failed"
            scan.items_parsed = items
            scan.total_cost_detected = round(total_cost, 2)
            scan.providers_detected = sorted(providers)
            scan.errors = "\n".join(errors[:50]) if errors else None
            scan.completed_at = datetime.utcnow()

            db.add(
                AuditLog(
                    tenant_id=tenant_id,
                    action="csv_import_completed",
                    user=username,
                    resource_type="scan_result",
                    resource_id=scan_id,
                    details=f"items={items};errors={len(errors)}",
                    timestamp=datetime.utcnow(),
                )
            )
            db.commit()
            return {
                "success": items > 0,
                "scan_id": scan_id,
                "items_imported": items,
                "total_cost": round(total_cost, 2),
                "providers": sorted(providers),
                "errors": errors[:20],
            }
        except Exception as exc:
            scan.status = "Failed"
            scan.errors = str(exc)
            scan.completed_at = datetime.utcnow()
            db.commit()
            return {"success": False, "scan_id": scan_id, "message": str(exc)}

    @staticmethod
    def export_costs_csv(db: Session, tenant_id: str, days: int = 30) -> str:
        from datetime import timedelta
        from sqlalchemy import func

        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            db.query(CostItem)
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= since)
            .order_by(CostItem.date.desc())
            .all()
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "date",
                "provider",
                "service",
                "account_id",
                "resource_id",
                "resource_name",
                "region",
                "cost",
                "usage_quantity",
                "usage_unit",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.date.isoformat() if r.date else "",
                    r.provider,
                    r.service,
                    r.account_id,
                    r.resource_id or "",
                    r.resource_name or "",
                    r.region or "",
                    r.cost,
                    r.usage_quantity,
                    r.usage_unit or "",
                ]
            )
        return output.getvalue()

    @staticmethod
    def export_costs_json(db: Session, tenant_id: str, days: int = 30) -> List[Dict[str, Any]]:
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            db.query(CostItem)
            .filter(CostItem.tenant_id == tenant_id, CostItem.date >= since)
            .order_by(CostItem.date.desc())
            .all()
        )
        return [
            {
                "date": r.date.isoformat() if r.date else None,
                "provider": r.provider,
                "service": r.service,
                "account_id": r.account_id,
                "resource_id": r.resource_id,
                "resource_name": r.resource_name,
                "region": r.region,
                "cost": r.cost,
                "usage_quantity": r.usage_quantity,
                "usage_unit": r.usage_unit,
            }
            for r in rows
        ]

    @staticmethod
    def list_import_history(db: Session, tenant_id: str) -> List[Dict]:
        scans = (
            db.query(ScanResult)
            .filter(ScanResult.tenant_id == tenant_id)
            .order_by(ScanResult.uploaded_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": s.id,
                "filename": s.filename,
                "status": s.status,
                "items_parsed": s.items_parsed,
                "total_cost_detected": s.total_cost_detected,
                "providers_detected": s.providers_detected,
                "uploaded_at": s.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                "errors": s.errors,
            }
            for s in scans
        ]

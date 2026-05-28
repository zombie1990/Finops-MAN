from datetime import datetime, timedelta
from typing import Any, Dict

from backend.app.connectors.base import BaseCloudAdapter, CloudSyncResult


class GCPAdapter(BaseCloudAdapter):
    provider = "GCP"

    def validate_config(self, config: Dict[str, Any]) -> None:
        if not config.get("project_id"):
            raise ValueError("Configuration GCP incomplète: project_id requis.")
        if not (config.get("service_account_json") or config.get("credentials_path")):
            raise ValueError(
                "Configuration GCP incomplète: service_account_json ou credentials_path requis."
            )

    def _credentials(self, config: Dict[str, Any]):
        from google.oauth2 import service_account
        import json

        if config.get("service_account_json"):
            info = config["service_account_json"]
            if isinstance(info, str):
                info = json.loads(info)
            return service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/cloud-billing.readonly"],
            )
        return service_account.Credentials.from_service_account_file(
            config["credentials_path"],
            scopes=["https://www.googleapis.com/auth/cloud-billing.readonly"],
        )

    def test_connection(self, config: Dict[str, Any]) -> CloudSyncResult:
        try:
            self.validate_config(config)
            from google.cloud import billing_v1

            credentials = self._credentials(config)
            client = billing_v1.CloudBillingClient(credentials=credentials)
            name = f"projects/{config['project_id']}"
            client.get_project_billing_info(name=name)
            return CloudSyncResult(success=True, message="Connexion GCP Billing API OK.")
        except ImportError:
            return CloudSyncResult(
                success=False,
                error="google-cloud-billing non installé. pip install google-cloud-billing",
            )
        except Exception as exc:
            return CloudSyncResult(success=False, error=str(exc))

    def fetch_cost_data(self, config: Dict[str, Any], days: int = 30) -> CloudSyncResult:
        """
        GCP billing détaillé nécessite BigQuery export (recommandé en prod).
        Ici: validation API + placeholder structuré si BigQuery non configuré.
        """
        test = self.test_connection(config)
        if not test.success:
            return test

        bq_dataset = config.get("bigquery_dataset")
        bq_table = config.get("bigquery_table")
        if bq_dataset and bq_table:
            try:
                from google.cloud import bigquery

                credentials = self._credentials(config)
                bq = bigquery.Client(
                    project=config.get("billing_project_id", config["project_id"]),
                    credentials=credentials,
                )
                query = f"""
                    SELECT
                      usage_start_time,
                      service.description AS service,
                      SUM(cost) AS total_cost
                    FROM `{config['project_id']}.{bq_dataset}.{bq_table}`
                    WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
                    GROUP BY usage_start_time, service
                    ORDER BY usage_start_time DESC
                    LIMIT 5000
                """
                rows = []
                for row in bq.query(query).result():
                    cost_val = float(row.total_cost or 0)
                    if cost_val <= 0:
                        continue
                    rows.append(
                        {
                            "account_id": config["project_id"],
                            "date": row.usage_start_time,
                            "provider": "GCP",
                            "service": row.service or "GCP Service",
                            "resource_id": f"gcp-{(row.service or 'service').lower().replace(' ', '-')}",
                            "resource_name": row.service or "GCP Service",
                            "region": config.get("region", "global"),
                            "cost": round(cost_val, 4),
                            "usage_quantity": 0.0,
                            "usage_unit": "USD",
                            "tags": config.get("tags") or {},
                            "carbon_emissions": round(cost_val * 0.07, 4),
                        }
                    )
                return CloudSyncResult(
                    success=True,
                    items_synced=len(rows),
                    message=f"{len(rows)} lignes GCP importées depuis BigQuery.",
                    cost_rows=rows,
                )
            except Exception as exc:
                return CloudSyncResult(success=False, error=f"BigQuery billing export: {exc}")

        return CloudSyncResult(
            success=False,
            error=(
                "BigQuery billing export non configuré. "
                "Ajoutez bigquery_dataset et bigquery_table dans config_json."
            ),
        )

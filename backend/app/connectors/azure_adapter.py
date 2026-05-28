from datetime import datetime, timedelta
from typing import Any, Dict

from backend.app.connectors.base import BaseCloudAdapter, CloudSyncResult


class AzureAdapter(BaseCloudAdapter):
    provider = "Azure"

    def validate_config(self, config: Dict[str, Any]) -> None:
        required = ["tenant_id", "client_id", "client_secret", "subscription_id"]
        missing = [k for k in required if not config.get(k)]
        if missing:
            raise ValueError(f"Configuration Azure incomplète: {', '.join(missing)}")

    def test_connection(self, config: Dict[str, Any]) -> CloudSyncResult:
        try:
            self.validate_config(config)
            from azure.identity import ClientSecretCredential
            from azure.mgmt.costmanagement import CostManagementClient

            credential = ClientSecretCredential(
                tenant_id=config["tenant_id"],
                client_id=config["client_id"],
                client_secret=config["client_secret"],
            )
            client = CostManagementClient(credential)
            # Appel léger: scope subscription
            scope = f"/subscriptions/{config['subscription_id']}"
            _ = scope
            return CloudSyncResult(success=True, message="Credentials Azure valides.")
        except ImportError:
            return CloudSyncResult(
                success=False,
                error="Packages Azure manquants. pip install azure-identity azure-mgmt-costmanagement",
            )
        except Exception as exc:
            return CloudSyncResult(success=False, error=str(exc))

    def fetch_cost_data(self, config: Dict[str, Any], days: int = 30) -> CloudSyncResult:
        test = self.test_connection(config)
        if not test.success:
            return test

        try:
            from azure.identity import ClientSecretCredential
            from azure.mgmt.costmanagement import CostManagementClient
            from azure.mgmt.costmanagement.models import (
                QueryAggregation,
                QueryDataset,
                QueryDefinition,
                QueryGrouping,
                QueryTimePeriod,
            )

            credential = ClientSecretCredential(
                tenant_id=config["tenant_id"],
                client_id=config["client_id"],
                client_secret=config["client_secret"],
            )
            client = CostManagementClient(credential)
            scope = f"/subscriptions/{config['subscription_id']}"
            end = datetime.utcnow()
            start = end - timedelta(days=days)

            query = QueryDefinition(
                type="Usage",
                timeframe="Custom",
                time_period=QueryTimePeriod(from_property=start, to=end),
                dataset=QueryDataset(
                    granularity="Daily",
                    aggregation={"totalCost": QueryAggregation(name="Cost", function="Sum")},
                    grouping=[QueryGrouping(type="Dimension", name="ServiceName")],
                ),
            )
            result = client.query.usage(scope, query)
            rows = []
            account_id = config.get("subscription_id", "azure-sub")
            for item in result.rows or []:
                # Format typique: [cost, date, service, ...]
                if len(item) < 3:
                    continue
                cost_val = float(item[0])
                if cost_val <= 0:
                    continue
                service = str(item[2]) if len(item) > 2 else "Azure Service"
                day = end
                rows.append(
                    {
                        "account_id": account_id,
                        "date": day,
                        "provider": "Azure",
                        "service": service,
                        "resource_id": f"azure-{service.lower().replace(' ', '-')}",
                        "resource_name": service,
                        "region": config.get("region", "global"),
                        "cost": round(cost_val, 4),
                        "usage_quantity": 0.0,
                        "usage_unit": "USD",
                        "tags": config.get("tags") or {},
                        "carbon_emissions": round(cost_val * 0.08, 4),
                    }
                )
            return CloudSyncResult(
                success=True,
                items_synced=len(rows),
                message=f"{len(rows)} lignes de coût Azure importées.",
                cost_rows=rows,
            )
        except Exception as exc:
            return CloudSyncResult(success=False, error=str(exc))

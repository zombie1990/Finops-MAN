from datetime import datetime, timedelta
from typing import Any, Dict

from backend.app.connectors.base import BaseCloudAdapter, CloudSyncResult


class AWSAdapter(BaseCloudAdapter):
    provider = "AWS"

    def validate_config(self, config: Dict[str, Any]) -> None:
        required = ["access_key_id", "secret_access_key", "region"]
        missing = [k for k in required if not config.get(k)]
        if missing:
            raise ValueError(f"Configuration AWS incomplète: {', '.join(missing)}")

    def test_connection(self, config: Dict[str, Any]) -> CloudSyncResult:
        try:
            self.validate_config(config)
            import boto3

            client = boto3.client(
                "ce",
                aws_access_key_id=config["access_key_id"],
                aws_secret_access_key=config["secret_access_key"],
                region_name=config.get("region", "us-east-1"),
            )
            end = datetime.utcnow().date()
            start = end - timedelta(days=7)
            client.get_cost_and_usage(
                TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
            )
            return CloudSyncResult(success=True, message="Connexion AWS Cost Explorer OK.")
        except ImportError:
            return CloudSyncResult(
                success=False,
                error="boto3 non installé. Exécutez: pip install boto3",
            )
        except Exception as exc:
            return CloudSyncResult(success=False, error=str(exc))

    def fetch_cost_data(self, config: Dict[str, Any], days: int = 30) -> CloudSyncResult:
        test = self.test_connection(config)
        if not test.success:
            return test

        import boto3

        client = boto3.client(
            "ce",
            aws_access_key_id=config["access_key_id"],
            aws_secret_access_key=config["secret_access_key"],
            region_name=config.get("region", "us-east-1"),
        )
        end = datetime.utcnow().date()
        start = end - timedelta(days=days)
        response = client.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        rows = []
        account_id = config.get("account_id", "aws-account")
        for block in response.get("ResultsByTime", []):
            day = datetime.strptime(block["TimePeriod"]["Start"], "%Y-%m-%d")
            for group in block.get("Groups", []):
                service = group["Keys"][0]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                if amount <= 0:
                    continue
                rows.append(
                    {
                        "account_id": account_id,
                        "date": day,
                        "provider": "AWS",
                        "service": service,
                        "resource_id": f"aws-{service.lower().replace(' ', '-')}",
                        "resource_name": service,
                        "region": config.get("region", "us-east-1"),
                        "cost": round(amount, 4),
                        "usage_quantity": 0.0,
                        "usage_unit": "USD",
                        "tags": config.get("tags") or {},
                        "carbon_emissions": round(amount * 0.085, 4),
                    }
                )

        return CloudSyncResult(
            success=True,
            items_synced=len(rows),
            message=f"{len(rows)} lignes de coût AWS importées.",
            cost_rows=rows,
        )

from typing import Dict

from backend.app.connectors.aws_adapter import AWSAdapter
from backend.app.connectors.azure_adapter import AzureAdapter
from backend.app.connectors.base import CloudSyncResult
from backend.app.connectors.gcp_adapter import GCPAdapter

_ADAPTERS = {
    "AWS": AWSAdapter(),
    "Azure": AzureAdapter(),
    "GCP": GCPAdapter(),
}


def get_adapter(provider: str):
    adapter = _ADAPTERS.get(provider)
    if not adapter:
        raise ValueError(f"Provider cloud non supporté pour sync réel: {provider}")
    return adapter


def sync_cloud_connector(provider: str, config: Dict, days: int = 30) -> CloudSyncResult:
    try:
        adapter = get_adapter(provider)
        adapter.validate_config(config or {})
        return adapter.fetch_cost_data(config, days=days)
    except ValueError as exc:
        return CloudSyncResult(success=False, error=str(exc))
    except Exception as exc:
        return CloudSyncResult(success=False, error=str(exc))


def test_cloud_connector(provider: str, config: Dict) -> CloudSyncResult:
    try:
        adapter = get_adapter(provider)
        adapter.validate_config(config or {})
        return adapter.test_connection(config)
    except ValueError as exc:
        return CloudSyncResult(success=False, error=str(exc))
    except Exception as exc:
        return CloudSyncResult(success=False, error=str(exc))

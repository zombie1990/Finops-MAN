from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CloudSyncResult:
    success: bool
    items_synced: int = 0
    message: str = ""
    error: Optional[str] = None
    cost_rows: List[Dict[str, Any]] = field(default_factory=list)


class BaseCloudAdapter:
    provider: str = "UNKNOWN"

    def validate_config(self, config: Dict[str, Any]) -> None:
        raise NotImplementedError

    def test_connection(self, config: Dict[str, Any]) -> CloudSyncResult:
        raise NotImplementedError

    def fetch_cost_data(self, config: Dict[str, Any], days: int = 30) -> CloudSyncResult:
        raise NotImplementedError

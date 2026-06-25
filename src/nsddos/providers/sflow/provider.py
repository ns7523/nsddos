"""sFlow-RT provider runtime helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from nsddos.providers.base import BaseProvider
from nsddos.constants import DEFAULT_SFLOWRT_PORT, get_sflowrt_jar


class SFlowProvider(BaseProvider):
    """sFlow-RT provider status and validation."""

    def __init__(
        self,
        api_url: str | None = None,
        artifact_path: Path | None = None,
    ) -> None:
        self.artifact_path = artifact_path or get_sflowrt_jar()
        self.api_url = api_url or f"http://127.0.0.1:{DEFAULT_SFLOWRT_PORT}"

    def artifact_exists(self) -> bool:
        """Check host artifact availability."""
        return self.artifact_path.exists()

    def is_reachable(self) -> bool:
        """Check sFlow-RT API reachability."""
        try:
            with urlopen(self.api_url, timeout=3) as response:
                return 200 <= response.status < 500
        except (OSError, URLError):
            return False

    def _json_get(self, path: str) -> Any:
        """Read JSON endpoint."""
        try:
            with urlopen(f"{self.api_url}{path}", timeout=3) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError):
            return None

    def flows(self) -> list[dict[str, Any]]:
        """Return sample active flows."""
        payload = self._json_get("/flows/json?maxFlows=1&timeout=1")
        return payload if isinstance(payload, list) else []

    def metrics(self) -> Any:
        """Return metrics payload."""
        return self._json_get("/metric/ALL/json")

    def topology(self) -> Any:
        """Return topology payload."""
        return self._json_get("/topology/json")

    def start(self) -> None:
        """Validate runtime prerequisites."""
        if not self.artifact_exists():
            raise RuntimeError(f"sFlow-RT jar missing: {self.artifact_path}")

    def stop(self) -> None:
        """Stop provider placeholder."""

    def status(self) -> dict[str, Any]:
        """Return provider status."""
        artifact_exists = self.artifact_exists()
        reachable = self.is_reachable()
        flows_payload = (
            self._json_get("/flows/json?maxFlows=1&timeout=1") if reachable else None
        )
        flows = flows_payload if isinstance(flows_payload, list) else []
        metrics = self.metrics() if reachable else None
        topology = self.topology() if reachable else None
        return {
            "provider": "sflowrt",
            "artifact": str(self.artifact_path),
            "artifact_exists": artifact_exists,
            "endpoint": self.api_url,
            "reachable": reachable,
            "flows_accessible": flows_payload is not None,
            "metrics_accessible": metrics is not None,
            "topology_accessible": topology is not None,
            "active_flow_count": len(flows),
            "ready": artifact_exists and reachable,
        }


def resolve_sflowrt_api_url(config: dict[str, Any]) -> str:
    """Resolve sFlow-RT HTTP endpoint from runtime config."""
    runtime_endpoint = (
        config.get("runtime", {})
        .get("live", {})
        .get("providers", {})
        .get("sflowrt", {})
        .get("endpoint")
    )
    if isinstance(runtime_endpoint, str) and runtime_endpoint.strip():
        return runtime_endpoint.strip()
    return f"http://127.0.0.1:{DEFAULT_SFLOWRT_PORT}"

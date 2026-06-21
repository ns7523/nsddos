"""Floodlight provider runtime helpers."""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from nsddos.constants import (
    DEFAULT_FLOODLIGHT_OF_PORT,
    DEFAULT_FLOODLIGHT_PORT,
    FLOODLIGHT_JAR,
)
from nsddos.providers.base import BaseProvider


class FloodlightProvider(BaseProvider):
    """Floodlight provider status and validation."""

    def __init__(
        self,
        api_url: str | None = None,
        artifact_path: Path = FLOODLIGHT_JAR,
        controller_host: str = "127.0.0.1",
        controller_port: int = DEFAULT_FLOODLIGHT_OF_PORT,
    ) -> None:
        self.artifact_path = artifact_path
        self.api_url = api_url or f"http://127.0.0.1:{DEFAULT_FLOODLIGHT_PORT}"
        self.controller_host = controller_host
        self.controller_port = controller_port

    def artifact_exists(self) -> bool:
        """Check host artifact availability."""
        return self.artifact_path.exists()

    def is_reachable(self) -> bool:
        """Check controller REST reachability."""
        try:
            with urlopen(f"{self.api_url}/wm/core/health/json", timeout=3) as response:
                return 200 <= response.status < 500
        except (OSError, URLError):
            return False

    def controller_port_open(self) -> bool:
        """Check OpenFlow controller port."""
        try:
            with socket.create_connection(
                (self.controller_host, self.controller_port),
                timeout=3,
            ):
                return True
        except OSError:
            return False

    def _json_get(self, path: str) -> Any:
        """Read JSON endpoint."""
        try:
            with urlopen(f"{self.api_url}{path}", timeout=3) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError):
            return None

    def _json_request(self, path: str, *, method: str, payload: dict[str, Any] | None = None) -> Any:
        """Send JSON request."""
        body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.api_url}{path}",
            data=body,
            headers={"content-type": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=3) as response:
                data = response.read().decode("utf-8")
                return json.loads(data) if data else {}
        except (OSError, URLError, json.JSONDecodeError):
            return None

    def switches(self) -> list[dict[str, Any]]:
        """Return registered switches."""
        payload = self._json_get("/wm/core/controller/switches/json")
        return payload if isinstance(payload, list) else []

    def flow_stats(self) -> dict[str, Any]:
        """Return switch flow stats payload."""
        payload = self._json_get("/wm/core/switch/all/flow/json")
        return payload if isinstance(payload, dict) else {}

    def flow_stats_accessible(self) -> bool:
        """Check whether Floodlight can query switch flow stats."""
        payload = self.flow_stats()
        if not payload:
            return False
        first_value = next(iter(payload.values()), None)
        if isinstance(first_value, dict):
            flattened = " ".join(str(item) for item in first_value.values())
            if "not supported by the switch's OpenFlow version" in flattened:
                return False
        return True

    def forwarding_programmed(self) -> bool:
        """Check whether controller reports at least one installed flow."""
        payload = self.flow_stats()
        if not payload or not self.flow_stats_accessible():
            return False
        for switch_entries in payload.values():
            if isinstance(switch_entries, list) and switch_entries:
                return True
        return False

    def push_static_flow(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Push static flow entry."""
        response = self._json_request("/wm/staticflowentrypusher/json", method="POST", payload=payload)
        return response if isinstance(response, dict) else {}

    def list_static_flows(self) -> dict[str, Any]:
        """List static flow entries."""
        payload = self._json_get("/wm/staticflowentrypusher/list/all/json")
        return payload if isinstance(payload, dict) else {}

    def static_flow_exists(self, rule_id: str) -> bool:
        """Check if named static flow exists."""
        flows = self.list_static_flows()
        for switch_entries in flows.values():
            if isinstance(switch_entries, dict) and rule_id in switch_entries:
                return True
        return False

    def start(self) -> None:
        """Validate controller startup prerequisites."""
        if not self.artifact_exists():
            raise RuntimeError(f"Floodlight jar missing: {self.artifact_path}")

    def stop(self) -> None:
        """Stop provider placeholder."""

    def status(self) -> dict[str, Any]:
        """Return provider status."""
        artifact_exists = self.artifact_exists()
        reachable = self.is_reachable()
        switches = self.switches() if reachable else []
        flow_stats_accessible = self.flow_stats_accessible() if reachable and switches else False
        return {
            "provider": "floodlight",
            "artifact": str(self.artifact_path),
            "artifact_exists": artifact_exists,
            "endpoint": self.api_url,
            "controller_port": f"{self.controller_host}:{self.controller_port}",
            "controller_port_open": self.controller_port_open(),
            "reachable": reachable,
            "switch_count": len(switches),
            "switches": [switch.get("switchDPID", "unknown") for switch in switches],
            "flow_stats_accessible": flow_stats_accessible,
            "forwarding_programmed": self.forwarding_programmed() if flow_stats_accessible else False,
            "ready": artifact_exists and reachable,
        }

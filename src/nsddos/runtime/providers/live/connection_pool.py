"""Deterministic live provider connection manager."""

from __future__ import annotations

import json
from dataclasses import dataclass
from time import monotonic, sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


@dataclass(frozen=True)
class ConnectionPolicy:
    timeout_seconds: float
    retry_count: int
    retry_delay_seconds: float = 0.05


@dataclass(frozen=True)
class ConnectionResult:
    ok: bool
    status_code: int
    payload: Any
    latency_ms: float
    error: str = ""


class DeterministicConnectionPool:
    """Reusable deterministic fetch helper."""

    def __init__(self, policy: ConnectionPolicy) -> None:
        self.policy = policy

    def get_json(self, url: str) -> ConnectionResult:
        attempts = max(1, self.policy.retry_count + 1)
        last_error = ""
        last_status = 0
        start = monotonic()
        for attempt in range(attempts):
            try:
                with urlopen(url, timeout=self.policy.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    return ConnectionResult(
                        ok=True,
                        status_code=int(getattr(response, "status", 200)),
                        payload=payload,
                        latency_ms=(monotonic() - start) * 1000,
                    )
            except HTTPError as exc:
                last_error = str(exc)
                last_status = int(exc.code)
            except (OSError, URLError, json.JSONDecodeError) as exc:
                last_error = str(exc)
            if attempt < attempts - 1:
                sleep(self.policy.retry_delay_seconds)
        return ConnectionResult(
            ok=False,
            status_code=last_status,
            payload=None,
            latency_ms=(monotonic() - start) * 1000,
            error=last_error or "connection_failed",
        )

"""Runtime readiness utilities."""

from __future__ import annotations

import time
from typing import Callable
from urllib.error import URLError
from urllib.request import urlopen

from nsddos.runtime.models import HealthResult


def wait_for_http(
    name: str,
    url: str,
    timeout: int = 60,
    interval: float = 2.0,
) -> HealthResult:
    """Wait until HTTP endpoint responds."""
    deadline = time.monotonic() + timeout
    last_error = "timeout"
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    return HealthResult(
                        name=name,
                        ok=True,
                        detail=f"reachable: {url}",
                        category="runtime",
                    )
                last_error = f"http {response.status}"
        except (OSError, URLError) as exc:
            last_error = str(exc)
        time.sleep(interval)
    return HealthResult(name=name, ok=False, detail=last_error, category="runtime")


def wait_for_check(
    name: str,
    check: Callable[[], bool],
    detail: str,
    timeout: int = 30,
    interval: float = 2.0,
) -> HealthResult:
    """Wait until callable returns True."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return HealthResult(name=name, ok=True, detail=detail, category="runtime")
        time.sleep(interval)
    return HealthResult(name=name, ok=False, detail=f"timeout: {detail}", category="runtime")

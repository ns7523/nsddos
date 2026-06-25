"""Background UI launcher for startup orchestration."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import urlopen

from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.bootstrap.state import UILaunchResult

UI_MODERN_MARKERS = (
    "NSDDOS",
    "SYSTEM",
    "THREAT LEVEL",
    "/static/css/app.css",
)
UI_HEALTH_PATH = "/ui/healthz"


def _fetch_ui_html(url: str) -> str:
    """Fetch root HTML for UI validation."""

    with urlopen(url, timeout=6) as response:
        return response.read(4096).decode("utf-8", "ignore")


def _health_url(url: str) -> str:
    """Return lightweight UI health endpoint for readiness checks."""

    base = url if url.endswith("/") else f"{url}/"
    return urljoin(base, UI_HEALTH_PATH.lstrip("/"))


def ui_reachable(url: str) -> bool:
    """Return whether UI root is reachable."""

    try:
        with urlopen(_health_url(url), timeout=6) as response:
            return 200 <= response.status < 500
    except (OSError, URLError):
        return False


def ui_is_modern(url: str) -> bool:
    """Return whether served UI matches redesigned SSR shell."""

    try:
        html = _fetch_ui_html(url)
    except (OSError, URLError):
        return False
    return all(marker in html for marker in UI_MODERN_MARKERS)


def replace_listener_on_port(
    port: int, *, exclude_pid: int | None = None
) -> tuple[int, ...]:
    """Terminate existing listener processes on given port."""

    result = subprocess.run(
        ("lsof", "-ti", f"tcp:{port}"),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in {0, 1}:
        return ()

    terminated: list[int] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid = int(line)
        except ValueError:
            continue
        if exclude_pid is not None and pid == exclude_pid:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            continue
        terminated.append(pid)
    return tuple(terminated)


def launch_ui_background(
    host: str = DEFAULT_STARTUP_PROFILE.ui_host,
    port: int = DEFAULT_STARTUP_PROFILE.ui_port,
) -> UILaunchResult:
    """Launch UI in background if not already reachable."""

    url = DEFAULT_STARTUP_PROFILE.ui_url
    if ui_reachable(url) and ui_is_modern(url):
        return UILaunchResult(launched=False, reachable=True, ui_url=url)
    terminated = ()
    if ui_reachable(url) and not ui_is_modern(url):
        terminated = replace_listener_on_port(port)
        time.sleep(0.5)
    elif not ui_reachable(url):
        terminated = replace_listener_on_port(port)
    if terminated:
        time.sleep(0.5)

    subprocess.Popen(
        (
            sys.executable,
            "-m",
            "uvicorn",
            "nsddos.ui.app:app",
            "--host",
            host,
            "--port",
            str(port),
        ),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if ui_reachable(url):
            return UILaunchResult(launched=True, reachable=True, ui_url=url)
        time.sleep(0.5)
    return UILaunchResult(launched=True, reachable=False, ui_url=url)

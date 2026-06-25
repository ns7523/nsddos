"""Startup orchestration constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nsddos.constants import APP_DIR


@dataclass(frozen=True)
class StartupProfile:
    """One-command startup profile."""

    container_names: tuple[str, ...]
    required_health_checks: tuple[str, ...]
    ui_host: str
    ui_port: int
    health_timeout_seconds: int
    health_poll_interval_seconds: int
    session_path: Path

    @property
    def ui_url(self) -> str:
        """Return UI URL."""

        return f"http://{self.ui_host}:{self.ui_port}"


DEFAULT_STARTUP_PROFILE = StartupProfile(
    container_names=(
        "nsddos-floodlight",
        "nsddos-sflowrt",
        "nsddos-labhost",
        "nsddos-detector",
    ),
    required_health_checks=(
        "docker_daemon",
        "containers",
        "floodlight",
        "sflowrt",
        "mininet",
        "ovs",
    ),
    ui_host="127.0.0.1",
    ui_port=8010,
    health_timeout_seconds=90,
    health_poll_interval_seconds=2,
    session_path=APP_DIR / "session.json",
)

REQUIRED_STARTUP_REQUIREMENTS = (
    "Install Docker",
    "Install Docker Compose",
    "Start Docker Daemon",
    "Configure Docker Permissions",
    "Create Runtime Directories",
    "Download Runtime Assets",
)

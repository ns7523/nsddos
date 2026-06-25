"""Environment detection for terminal onboarding."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from nsddos.compose import resolve_compose_command


@dataclass(frozen=True)
class ToolStatus:
    """Tool installation state."""

    name: str
    installed: bool
    detail: str | None = None


@dataclass(frozen=True)
class EnvironmentSnapshot:
    """Detected terminal environment."""

    os_name: str
    os_family: str
    python_version: str
    docker: ToolStatus
    docker_daemon_running: bool
    git: ToolStatus
    virtualenv_active: bool


def _os_family(os_name: str) -> str:
    normalized = os_name.lower()
    if normalized == "darwin":
        return "macOS"
    if normalized == "linux":
        return "Linux"
    if normalized == "windows":
        return "Windows"
    return os_name


def _detect_tool(name: str) -> ToolStatus:
    path = shutil.which(name)
    return ToolStatus(name=name, installed=path is not None, detail=path)


def _detect_docker_daemon(docker: ToolStatus) -> bool:
    if not docker.installed:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _detect_docker_compose(docker: ToolStatus) -> ToolStatus:
    if not docker.installed:
        return ToolStatus(name="docker-compose", installed=False, detail=None)
    try:
        command = resolve_compose_command()
    except (OSError, subprocess.SubprocessError):
        return ToolStatus(name="docker-compose", installed=False, detail=None)
    if command is None:
        return ToolStatus(name="docker-compose", installed=False, detail=None)
    return ToolStatus(
        name="docker-compose",
        installed=True,
        detail=" ".join(command),
    )


def _detect_available_memory_bytes() -> int:
    if not hasattr(os, "sysconf"):
        return 0
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        page_count = int(os.sysconf("SC_PHYS_PAGES"))
    except (OSError, ValueError):
        return 0
    return max(page_size * page_count, 0)


def _detect_available_disk_bytes(path: Path | None = None) -> int:
    target = path or Path.cwd()
    try:
        usage = shutil.disk_usage(target)
    except OSError:
        return 0
    if hasattr(usage, "free"):
        return int(usage.free)
    return int(usage[2])


def _virtualenv_active() -> bool:
    return bool(os.getenv("VIRTUAL_ENV")) or sys.prefix != getattr(
        sys, "base_prefix", sys.prefix
    )


def detect_environment() -> EnvironmentSnapshot:
    """Collect deterministic terminal environment details."""

    os_name = platform.system() or "Unknown"
    docker = _detect_tool("docker")
    return EnvironmentSnapshot(
        os_name=os_name,
        os_family=_os_family(os_name),
        python_version=platform.python_version(),
        docker=docker,
        docker_daemon_running=_detect_docker_daemon(docker),
        git=_detect_tool("git"),
        virtualenv_active=_virtualenv_active(),
    )

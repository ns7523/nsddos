"""Environment scan entrypoints for setup wizard."""

from __future__ import annotations

import platform

from nsddos.bootstrap.environment import (
    _detect_available_disk_bytes,
    _detect_available_memory_bytes,
    _detect_docker_compose,
    _detect_docker_daemon,
    _detect_tool,
    _os_family,
    _virtualenv_active,
)
from nsddos.bootstrap.permissions import detect_docker_permissions_ready, detect_missing_runtime_directories
from nsddos.bootstrap.state import EnvironmentScan


def collect_environment_scan() -> EnvironmentScan:
    """Collect extended setup scan."""

    os_name = platform.system() or "Unknown"
    docker = _detect_tool("docker")
    return EnvironmentScan(
        os_name=os_name,
        os_family=_os_family(os_name),
        python_version=platform.python_version(),
        virtualenv_active=_virtualenv_active(),
        docker=docker,
        docker_daemon_running=_detect_docker_daemon(docker),
        docker_compose=_detect_docker_compose(docker),
        docker_permissions_ready=detect_docker_permissions_ready(docker.installed, _os_family(os_name)),
        git=_detect_tool("git"),
        available_memory_bytes=_detect_available_memory_bytes(),
        available_disk_bytes=_detect_available_disk_bytes(),
        missing_runtime_directories=detect_missing_runtime_directories(),
    )

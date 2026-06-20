"""Runtime capability detection."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

from nsddos.constants import MININET_BIN, OVS_VSCTL_BIN
from nsddos.docker_manager import DockerManager
from nsddos.providers.docker_helper import helper_running
from nsddos.runtime.models import CapabilityMap


def _cmd_ok(command: list[str]) -> bool:
    """Return True when command exits 0."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return False
    return result.returncode == 0


def _has_passwordless_sudo() -> bool:
    """Detect passwordless sudo."""
    return _cmd_ok(["sudo", "-n", "true"])


def detect_runtime_capabilities() -> CapabilityMap:
    """Detect normalized runtime capabilities."""
    system = platform.system().lower()
    release = platform.release().lower()
    docker = DockerManager()
    ovs_installed = _cmd_ok([str(OVS_VSCTL_BIN), "--version"])
    ovs_service = _cmd_ok([str(OVS_VSCTL_BIN), "show"]) if ovs_installed else False
    mininet_supported = Path(MININET_BIN).exists()
    sudo_available = _cmd_ok(["sudo", "-V"])
    passwordless_sudo = _has_passwordless_sudo() if sudo_available else False
    java_available = _cmd_ok(["java", "-version"])
    linux_kernel = system == "linux"
    wsl2 = linux_kernel and ("microsoft" in release or "wsl2" in release)
    docker_installed = docker.is_docker_installed()
    docker_daemon = docker.is_daemon_running() if docker_installed else False
    helper = docker_daemon and helper_running()
    if helper:
        ovs_installed = True
        ovs_service = True
        mininet_supported = True
        passwordless_sudo = True
    container_networking = docker_daemon and (linux_kernel or helper)
    openflow_compatible = (linux_kernel and ovs_installed) or helper
    sflow_capable = (linux_kernel and ovs_installed) or helper

    detail = ",".join(
        [
            f"platform={system}",
            f"kernel={release}",
            f"docker={docker_daemon}",
            f"ovs={ovs_service}",
            f"mininet={mininet_supported}",
            f"helper={helper}",
        ]
    )
    return CapabilityMap(
        platform=system,
        kernel=release,
        docker_installed=docker_installed,
        docker_daemon=docker_daemon,
        ovs_installed=ovs_installed,
        ovs_service=ovs_service,
        mininet_supported=mininet_supported,
        linux_kernel=linux_kernel,
        sudo_available=sudo_available,
        passwordless_sudo=passwordless_sudo,
        wsl2=wsl2,
        container_networking=container_networking,
        openflow_compatible=openflow_compatible,
        sflow_capable=sflow_capable,
        java_available=java_available,
        detail=detail,
    )

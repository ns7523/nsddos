"""Runtime capability detection."""

from __future__ import annotations

import platform
from nsddos.docker_manager import DockerManager
from nsddos.runtime.executor import RuntimeExecutor
from nsddos.runtime.models import CapabilityMap


def detect_runtime_capabilities() -> CapabilityMap:
    """Detect normalized runtime capabilities."""
    system = platform.system().lower()
    release = platform.release().lower()
    docker = DockerManager()
    executor = RuntimeExecutor()
    linux_kernel = system == "linux"
    wsl2 = linux_kernel and ("microsoft" in release or "wsl2" in release)
    docker_installed = docker.is_docker_installed()
    docker_daemon = docker.is_daemon_running() if docker_installed else False
    helper = docker_daemon and executor.lab_container_running()
    ovs_installed = docker_daemon
    ovs_service = helper
    mininet_supported = helper
    sudo_available = False
    passwordless_sudo = False
    java_available = True
    container_networking = docker_daemon
    openflow_compatible = helper
    sflow_capable = helper

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

"""Open vSwitch command helpers."""

from __future__ import annotations

import subprocess

from nsddos.runtime.executor import RuntimeExecutor

_EXECUTOR = RuntimeExecutor()


def run_ovs_vsctl(
    args: list[str],
    timeout: int = 5,
) -> subprocess.CompletedProcess[str]:
    """Run ovs-vsctl inside labhost container."""

    if not _EXECUTOR.lab_container_running():
        return subprocess.CompletedProcess(
            args=["ovs-vsctl", *args],
            returncode=1,
            stdout="",
            stderr="labhost unavailable",
        )
    return _EXECUTOR.execute_lab(["ovs-vsctl", *args], timeout=timeout)


def run_ovs_ofctl(
    args: list[str],
    timeout: int = 5,
) -> subprocess.CompletedProcess[str]:
    """Run ovs-ofctl inside labhost container."""

    if not _EXECUTOR.lab_container_running():
        return subprocess.CompletedProcess(
            args=["ovs-ofctl", *args],
            returncode=1,
            stdout="",
            stderr="labhost unavailable",
        )
    return _EXECUTOR.execute_lab(["ovs-ofctl", *args], timeout=timeout)


def ovs_process_running(process_name: str = "ovs-vswitchd") -> bool:
    """Return whether OVS process is running in labhost."""

    if not _EXECUTOR.lab_container_running():
        return False
    return _EXECUTOR.execute_lab(["pgrep", process_name], timeout=5).returncode == 0

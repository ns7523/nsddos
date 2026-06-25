"""Docker-backed helper runtime utilities."""

from __future__ import annotations

import subprocess
from nsddos.runtime.executor import LAB_CONTAINER, RuntimeExecutor

LAB_HELPER_CONTAINER = LAB_CONTAINER
_EXECUTOR = RuntimeExecutor()


def docker_available() -> bool:
    """Return whether Docker CLI exists."""
    return _EXECUTOR.docker_available()


def helper_running() -> bool:
    """Return whether helper container is running."""
    return _EXECUTOR.lab_container_running()


def helper_exec(
    args: list[str],
    *,
    detached: bool = False,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    """Run command inside helper container."""
    return _EXECUTOR.execute_lab(args, detached=detached, timeout=timeout)


def helper_link_index_map() -> dict[str, str]:
    """Return helper interface names keyed by numeric link index."""
    return _EXECUTOR.lab_link_index_map()

"""Docker-backed helper runtime utilities."""

from __future__ import annotations

import os
import subprocess
from shutil import which


LAB_HELPER_CONTAINER = os.getenv("NSDDOS_LAB_HELPER_CONTAINER", "nsddos-labhost")


def docker_available() -> bool:
    """Return whether Docker CLI exists."""
    return which("docker") is not None


def helper_running() -> bool:
    """Return whether helper container is running."""
    if not docker_available():
        return False
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", LAB_HELPER_CONTAINER],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def helper_exec(
    args: list[str],
    *,
    detached: bool = False,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    """Run command inside helper container."""
    command = ["docker", "exec"]
    if detached:
        command.append("-d")
    command.extend([LAB_HELPER_CONTAINER, *args])
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def helper_link_index_map() -> dict[str, str]:
    """Return helper interface names keyed by numeric link index."""
    if not helper_running():
        return {}
    result = helper_exec(["ip", "-o", "link", "show"], timeout=10)
    if result.returncode != 0:
        return {}
    mapping: dict[str, str] = {}
    for line in result.stdout.splitlines():
        prefix, _, _rest = line.partition(": ")
        if not prefix:
            continue
        link_index = prefix.strip()
        remainder = line[len(prefix) + 2 :]
        name, _, _tail = remainder.partition(":")
        cleaned = name.split("@", 1)[0].strip()
        if link_index and cleaned:
            mapping[link_index] = cleaned
    return mapping

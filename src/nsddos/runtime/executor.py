"""Shared host/container execution utilities."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from shutil import which


LAB_CONTAINER = os.getenv("NSDDOS_LAB_HELPER_CONTAINER", "nsddos-labhost")


@dataclass(frozen=True)
class RuntimeExecutor:
    """Container-aware runtime executor."""

    lab_container: str = LAB_CONTAINER

    @staticmethod
    def docker_available() -> bool:
        """Return whether Docker CLI exists."""

        return which("docker") is not None

    def execute_on_host(
        self,
        args: list[str],
        *,
        timeout: int = 30,
        capture_output: bool = True,
        text: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Execute host command."""

        return subprocess.run(
            args,
            capture_output=capture_output,
            text=text,
            timeout=timeout,
            check=False,
        )

    def container_running(self, container: str) -> bool:
        """Return whether container is running."""

        if not self.docker_available():
            return False
        result = self.execute_on_host(
            ["docker", "inspect", "-f", "{{.State.Running}}", container],
            timeout=10,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    def lab_container_running(self) -> bool:
        """Return whether lab container is running."""

        return self.container_running(self.lab_container)

    def execute_in_container(
        self,
        container: str,
        args: list[str],
        *,
        detached: bool = False,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        """Execute command in container."""

        command = ["docker", "exec"]
        if detached:
            command.append("-d")
        command.extend([container, *args])
        return self.execute_on_host(command, timeout=timeout)

    def execute_lab(
        self,
        args: list[str],
        *,
        detached: bool = False,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        """Execute command in lab container."""

        return self.execute_in_container(
            self.lab_container,
            args,
            detached=detached,
            timeout=timeout,
        )

    def lab_link_index_map(self) -> dict[str, str]:
        """Return lab interface names keyed by numeric link index."""

        if not self.lab_container_running():
            return {}
        result = self.execute_lab(["ip", "-o", "link", "show"], timeout=10)
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

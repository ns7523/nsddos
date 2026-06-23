"""Shared Docker Compose backend resolution."""

from __future__ import annotations

import subprocess
from shutil import which


ComposeCommand = tuple[str, ...]


def resolve_compose_command() -> ComposeCommand | None:
    """Resolve preferred Compose backend command."""

    if which("docker") is not None:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return ("docker", "compose")
    if which("docker-compose") is not None:
        return ("docker-compose",)
    return None


def compose_backend_name(command: ComposeCommand) -> str:
    """Return human/backend label for resolved Compose command."""

    if command == ("docker", "compose"):
        return "docker-compose-v2"
    if command == ("docker-compose",):
        return "docker-compose-v1"
    return "docker-compose-unknown"

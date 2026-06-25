"""Permission and directory helpers for installer engine."""

from __future__ import annotations

import getpass
import grp
import os
from pathlib import Path

from nsddos.bootstrap.commands import SystemCommand, mkdir_command, subprocess_command
from nsddos.constants import RUNTIME_DIRECTORIES


def detect_docker_permissions_ready(docker_installed: bool, os_family: str) -> bool:
    """Detect whether Docker permissions look ready."""

    if not docker_installed:
        return False
    if os_family != "Linux":
        return True
    try:
        docker_group = grp.getgrnam("docker")
    except KeyError:
        return False
    user = getpass.getuser()
    return user in docker_group.gr_mem or os.getgid() == docker_group.gr_gid


def detect_missing_runtime_directories() -> tuple[str, ...]:
    """Detect missing runtime directory paths."""

    return tuple(str(path) for path in RUNTIME_DIRECTORIES if not Path(path).exists())


def build_runtime_directory_commands(
    paths: tuple[str, ...]
) -> tuple[SystemCommand, ...]:
    """Build runtime directory creation commands."""

    return tuple(mkdir_command("Create runtime directory", path) for path in paths)


def build_docker_permission_commands() -> tuple[SystemCommand, ...]:
    """Build Docker permission commands."""

    user = getpass.getuser()
    return (
        subprocess_command(
            "Add current user to docker group",
            ("sudo", "usermod", "-aG", "docker", user),
        ),
    )

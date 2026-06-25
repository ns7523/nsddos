"""Docker-related installer command generation."""

from __future__ import annotations

from nsddos.bootstrap.commands import SystemCommand, subprocess_command
from nsddos.bootstrap.os_profiles import OSProfile
from nsddos.bootstrap.package_manager import PackageManager, build_install_commands


def build_docker_install_commands(
    manager: PackageManager,
    os_profile: OSProfile,
) -> tuple[SystemCommand, ...]:
    """Build Docker install commands."""

    if os_profile.family == "Linux":
        return build_install_commands(manager, ("docker.io",))
    if os_profile.family == "macOS":
        return build_install_commands(manager, ("docker",))
    return ()


def build_docker_compose_install_commands(
    manager: PackageManager,
    os_profile: OSProfile,
) -> tuple[SystemCommand, ...]:
    """Build Docker Compose install commands."""

    if os_profile.family == "Linux":
        return build_install_commands(manager, ("docker-compose-plugin",))
    if os_profile.family == "macOS":
        return build_install_commands(manager, ("docker-compose",))
    return ()


def build_docker_daemon_commands(os_profile: OSProfile) -> tuple[SystemCommand, ...]:
    """Build Docker daemon start commands."""

    if os_profile.family == "Linux":
        return (
            subprocess_command(
                "Start Docker daemon",
                ("sudo", "systemctl", "start", "docker"),
                rollback_argv=("sudo", "systemctl", "stop", "docker"),
                reversible=True,
            ),
            subprocess_command(
                "Enable Docker daemon", ("sudo", "systemctl", "enable", "docker")
            ),
        )
    if os_profile.family == "macOS":
        return (subprocess_command("Launch Docker Desktop", ("open", "-a", "Docker")),)
    return ()

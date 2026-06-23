"""Package manager selection and package install commands."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.bootstrap.commands import SystemCommand, subprocess_command
from nsddos.bootstrap.os_profiles import OSProfile


@dataclass(frozen=True)
class PackageManager:
    """Selected package manager."""

    name: str
    supported: bool


def select_package_manager(profile: OSProfile) -> PackageManager:
    """Select package manager for OS profile."""

    return PackageManager(name=profile.package_manager, supported=profile.supported)


def build_install_commands(manager: PackageManager, packages: tuple[str, ...]) -> tuple[SystemCommand, ...]:
    """Build package install commands."""

    if not packages or not manager.supported:
        return ()
    if manager.name == "apt":
        return (
            subprocess_command("Update apt package index", ("sudo", "apt", "update")),
            subprocess_command("Install packages", ("sudo", "apt", "install", "-y", *packages)),
        )
    if manager.name == "brew":
        return tuple(
            subprocess_command(
                f"Install {package}",
                ("brew", "install", "--cask", package) if package == "docker" else ("brew", "install", package),
            )
            for package in packages
        )
    return ()

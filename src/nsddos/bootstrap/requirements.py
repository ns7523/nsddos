"""Requirement planning for setup wizard."""

from __future__ import annotations

from nsddos.bootstrap.state import (
    DeploymentProfile,
    EnvironmentScan,
    InstallRequirement,
)


def build_install_requirements(
    scan: EnvironmentScan,
    profile: DeploymentProfile,
    advisory: tuple[InstallRequirement, ...] = (),
) -> tuple[InstallRequirement, ...]:
    """Build ordered non-installing setup plan."""

    requirements: list[InstallRequirement] = []
    if not scan.docker.installed:
        requirements.append(
            InstallRequirement(
                "A", "Install Docker", "Docker engine required for NSDDOS runtime."
            )
        )
    if not scan.docker_compose.installed:
        requirements.append(
            InstallRequirement(
                "B",
                "Install Docker Compose",
                "Compose required for multi-service runtime orchestration.",
            )
        )
    if scan.docker.installed and not scan.docker_daemon_running:
        requirements.append(
            InstallRequirement(
                "C", "Start Docker Daemon", "Docker CLI present but daemon not running."
            )
        )
    if not scan.git.installed:
        requirements.append(
            InstallRequirement(
                "D",
                "Install Git",
                "Git required for source sync and developer workflows.",
            )
        )
    if not scan.virtualenv_active:
        requirements.append(
            InstallRequirement(
                "E",
                "Create Virtual Environment",
                "Create isolated Python environment before runtime setup.",
            )
        )
    if not scan.docker_permissions_ready:
        requirements.append(
            InstallRequirement(
                "F",
                "Configure Docker Permissions",
                "Grant current user Docker runtime access.",
            )
        )
    if scan.missing_runtime_directories:
        requirements.append(
            InstallRequirement(
                "G",
                "Create Runtime Directories",
                "Create required NSDDOS runtime directories.",
            )
        )
    if not scan.runtime_assets_ready:
        requirements.append(
            InstallRequirement(
                "H",
                "Download Runtime Assets",
                "Download and verify required runtime payloads.",
            )
        )
    requirements.extend(advisory)
    requirements.append(
        InstallRequirement(
            "I",
            "Build Containers",
            "Prepare container images after prerequisites are satisfied.",
        )
    )
    requirements.append(
        InstallRequirement(
            "J", "Initialize Runtime", "Initialize runtime state and configuration."
        )
    )
    return tuple(requirements)

"""Derived onboarding diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.bootstrap.environment import EnvironmentSnapshot

from . import theme


@dataclass(frozen=True)
class DiagnosticItem:
    """Terminal diagnostic row."""

    label: str
    status: str
    detail: str


@dataclass(frozen=True)
class QuickCommand:
    """Suggested onboarding command."""

    name: str
    description: str


def build_environment_diagnostics(
    snapshot: EnvironmentSnapshot,
) -> list[DiagnosticItem]:
    """Convert environment snapshot into terminal rows."""

    return [
        DiagnosticItem("OS", theme.STATUS_OK, snapshot.os_family),
        DiagnosticItem("Python", theme.STATUS_OK, snapshot.python_version),
        DiagnosticItem(
            "Docker",
            theme.STATUS_OK if snapshot.docker.installed else theme.STATUS_MISSING,
            "Installed" if snapshot.docker.installed else "Missing",
        ),
        DiagnosticItem(
            "Docker Daemon",
            theme.STATUS_OK if snapshot.docker_daemon_running else theme.STATUS_WARN,
            "Running" if snapshot.docker_daemon_running else "Stopped",
        ),
        DiagnosticItem(
            "Git",
            theme.STATUS_OK if snapshot.git.installed else theme.STATUS_MISSING,
            "Installed" if snapshot.git.installed else "Missing",
        ),
        DiagnosticItem(
            "Virtualenv",
            theme.STATUS_OK if snapshot.virtualenv_active else theme.STATUS_WARN,
            "Active" if snapshot.virtualenv_active else "Inactive",
        ),
    ]


def build_quick_commands() -> list[QuickCommand]:
    """Return deterministic quick commands."""

    return [
        QuickCommand("nsddos setup", "Prepare full environment in later step"),
        QuickCommand("nsddos start", "Start local runtime"),
        QuickCommand("nsddos doctor", "Inspect environment health"),
    ]


def readiness_label(snapshot: EnvironmentSnapshot) -> str:
    """Compute onboarding readiness label."""

    if (
        snapshot.docker.installed
        and snapshot.git.installed
        and snapshot.docker_daemon_running
    ):
        return theme.READY_LABEL
    return theme.DEGRADED_LABEL


def readiness_completed_steps(snapshot: EnvironmentSnapshot) -> int:
    """Return completed foundation checks."""

    return sum(
        (
            snapshot.docker.installed,
            snapshot.git.installed,
            snapshot.docker_daemon_running,
            snapshot.virtualenv_active,
        )
    )

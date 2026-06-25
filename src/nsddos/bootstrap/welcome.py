"""Welcome screen orchestration."""

from __future__ import annotations

from rich.console import Console, Group, RenderableType
from rich.table import Table

from nsddos.bootstrap.banner import build_banner_panel
from nsddos.bootstrap.diagnostics import (
    build_environment_diagnostics,
    build_quick_commands,
    readiness_completed_steps,
    readiness_label,
)
from nsddos.bootstrap.environment import EnvironmentSnapshot, detect_environment
from nsddos.bootstrap.terminal import (
    build_command_deck,
    build_environment_table,
    build_footer_line,
    build_operator_chips,
    build_operator_header,
    build_readiness_progress,
    create_console,
    section_panel,
)
from . import theme


def _build_readiness_table(snapshot: EnvironmentSnapshot) -> Table:
    table = Table(expand=True, box=None, pad_edge=False)
    table.add_column("Field", style="bold white")
    table.add_column("Value", style="bright_black")
    table.add_row("Status", readiness_label(snapshot))
    table.add_row("Launch Mode", "Operator console")
    table.add_row("Surface", "Bootstrap command center")
    table.add_row("Next Action", "Run command deck action")
    return table


def build_welcome_renderable(snapshot: EnvironmentSnapshot) -> RenderableType:
    """Build premium onboarding layout."""

    diagnostics = build_environment_diagnostics(snapshot)
    commands = build_quick_commands()
    completed = readiness_completed_steps(snapshot)
    total = 4
    header = build_operator_header(
        "Runtime Operator Surface",
        f"{snapshot.os_family} boot channel",
        theme.APP_DISPLAY_TAGLINE,
    )
    return Group(
        header,
        build_banner_panel(),
        section_panel("Environment Scan", build_environment_table(diagnostics)),
        build_operator_chips(
            (
                ("STATUS", readiness_label(snapshot)),
                ("PYTHON", snapshot.python_version),
                (
                    "DOCKER",
                    "CONNECTED" if snapshot.docker_daemon_running else "WAITING",
                ),
            )
        ),
        section_panel(
            "Readiness Matrix",
            Group(
                build_readiness_progress(completed=completed, total=total),
                _build_readiness_table(snapshot),
            ),
        ),
        build_command_deck(commands),
        build_footer_line(
            "NSDDOS operator console ready. Use command deck to continue."
        ),
    )


def render_welcome_screen(console: Console | None = None) -> EnvironmentSnapshot:
    """Render welcome screen and return detected snapshot."""

    active_console = console or create_console()
    snapshot = detect_environment()
    active_console.print(build_welcome_renderable(snapshot))
    return snapshot

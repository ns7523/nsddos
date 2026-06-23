"""CLI-facing reset command."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from nsddos.bootstrap.reset_engine import execute_reset
from nsddos.bootstrap.state import ResetResult
from nsddos.bootstrap.terminal import create_console


def run_reset_command(console: Console | None = None) -> ResetResult:
    """Run reset workflow."""

    active_console = console or create_console()
    result = execute_reset(active_console)
    active_console.print(
        Panel(
            "\n".join(
                [
                    f"[bold white]Stopped services: {len(result.stopped_services)}[/bold white]",
                    f"[bright_black]Deleted paths: {len(result.deleted_paths)}[/bright_black]",
                    f"[bright_black]Preserved config: {result.preserved_config_path}[/bright_black]",
                ]
            ),
            title="NSDDOS Reset",
            border_style="green" if result.success else "yellow",
        )
    )
    return result


def ensure_reset_success(result: ResetResult) -> None:
    """Raise nonzero when reset cancelled or failed."""

    if not result.success:
        raise typer.Exit(code=1)

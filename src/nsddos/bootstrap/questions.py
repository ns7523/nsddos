"""Interactive setup wizard questions."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.prompt import IntPrompt
from rich.table import Table

from nsddos.bootstrap.profiles import get_profile_by_choice, profile_choices
from nsddos.bootstrap.state import DeploymentProfile


def _build_profile_table() -> Table:
    table = Table(expand=True, box=None, pad_edge=False)
    table.add_column("Choice", style="bold bright_cyan", justify="center")
    table.add_column("Deployment Mode", style="bold white")
    table.add_column("Purpose", style="bright_black")
    for choice, profile in profile_choices():
        table.add_row(f"[{choice}]", profile.label, profile.description)
    return table


def ask_deployment_profile(console: Console) -> DeploymentProfile:
    """Prompt for deployment profile selection."""

    console.print(Panel(_build_profile_table(), title="Select Deployment Mode", border_style="cyan"))
    try:
        choice = IntPrompt.ask(
            "Select deployment mode",
            console=console,
            choices=[str(choice) for choice, _ in profile_choices()],
            default=1,
            show_default=True,
        )
    except (EOFError, KeyboardInterrupt):
        console.print(
            Panel(
                "Non-interactive input detected. Defaulting to Local Development.",
                border_style="yellow",
                title="Selection Fallback",
            )
        )
        choice = 1
    return get_profile_by_choice(int(choice))


def confirm_install(console: Console, prompt: str) -> bool:
    """Prompt for installation permission with safe fallback."""

    try:
        return bool(Confirm.ask(prompt, console=console, default=True))
    except (EOFError, KeyboardInterrupt):
        return False

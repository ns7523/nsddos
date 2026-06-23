"""Doctor repair execution engine."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from nsddos.bootstrap.container_repair import repair_containers
from nsddos.bootstrap.installer import execute_install_plan
from nsddos.bootstrap.planner import build_dependency_plan
from nsddos.bootstrap.profiles import LOCAL_DEVELOPMENT
from nsddos.bootstrap.questions import confirm_install
from nsddos.bootstrap.runtime_repair import repair_runtime_state
from nsddos.bootstrap.session_repair import recreate_startup_session
from nsddos.bootstrap.setup import collect_environment_scan
from nsddos.bootstrap.startup_profiles import REQUIRED_STARTUP_REQUIREMENTS
from nsddos.bootstrap.state import RepairAction
from nsddos.bootstrap.ui_launcher import launch_ui_background


def execute_repairs(console: Console, actions: tuple[RepairAction, ...]) -> tuple[str, ...]:
    """Execute approved repairs."""

    if not actions:
        return ()
    if not confirm_install(console, "Apply recommended repairs?"):
        return ()
    progress = Progress(
        SpinnerColumn(style="bright_cyan"),
        TextColumn("[bold white]Repairing[/bold white]"),
        BarColumn(bar_width=24, complete_style="bright_cyan", finished_style="bright_cyan"),
        TextColumn("[bright_cyan]{task.completed}/{task.total}[/bright_cyan]"),
        console=console,
    )
    task_id = progress.add_task("repair", total=len(actions), completed=0)
    console.print(progress)
    applied: list[str] = []
    for action in actions:
        success = False
        if action.action_type == "installer":
            scan = collect_environment_scan()
            plan = build_dependency_plan(scan, LOCAL_DEVELOPMENT)
            result = execute_install_plan(
                console,
                plan,
                scan,
                auto_approve_required=True,
                allowed_titles=REQUIRED_STARTUP_REQUIREMENTS + ("Install Git",),
            )
            success = result.failed_requirement is None
        elif action.action_type == "container_repair":
            success = repair_containers(console)
        elif action.action_type == "runtime_repair":
            repair_runtime_state()
            success = True
        elif action.action_type == "ui_restart":
            success = launch_ui_background().reachable
        elif action.action_type == "session_repair":
            recreate_startup_session()
            success = True
        elif action.action_type in {"venv_repair", "git_repair"}:
            scan = collect_environment_scan()
            plan = build_dependency_plan(scan, LOCAL_DEVELOPMENT)
            allowed = ("Create Virtual Environment",) if action.action_type == "venv_repair" else ("Install Git",)
            result = execute_install_plan(
                console,
                plan,
                scan,
                auto_approve_required=True,
                allowed_titles=allowed,
            )
            success = result.failed_requirement is None
        if success:
            applied.append(action.title)
        else:
            console.print(
                Panel(
                    f"{action.title} failed.",
                    title="Repair Failure",
                    border_style="red",
                )
            )
        progress.update(task_id, advance=1)
    return tuple(applied)

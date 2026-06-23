"""Automatic installer engine for setup wizard."""

from __future__ import annotations

import sys
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from nsddos.bootstrap.commands import SystemCommand, runtime_init_command, subprocess_command, venv_command
from nsddos.bootstrap.docker_install import (
    build_docker_compose_install_commands,
    build_docker_daemon_commands,
    build_docker_install_commands,
)
from nsddos.bootstrap.executors import CommandExecutionResult, run_system_command
from nsddos.bootstrap.os_profiles import OSProfile, detect_os_profile
from nsddos.bootstrap.package_manager import build_install_commands, select_package_manager
from nsddos.bootstrap.permissions import build_docker_permission_commands, build_runtime_directory_commands
from nsddos.bootstrap.questions import confirm_install
from nsddos.bootstrap.rollback import rollback_commands
from nsddos.bootstrap.state import DependencyPlan, EnvironmentScan, InstallRequirement
from nsddos.bootstrap.transactions import (
    append_transaction_record,
    build_transaction_record,
    create_transaction_log,
)


@dataclass(frozen=True)
class InstallerRunResult:
    """Installer execution summary."""

    applied: tuple[CommandExecutionResult, ...]
    skipped_requirements: tuple[str, ...]
    failed_requirement: str | None
    rollback_results: tuple[CommandExecutionResult, ...]


def commands_for_requirement(
    requirement: InstallRequirement,
    scan: EnvironmentScan,
    os_profile: OSProfile,
) -> tuple[SystemCommand, ...]:
    """Map planned requirement to executable commands."""

    manager = select_package_manager(os_profile)
    if requirement.title == "Install Docker":
        return build_docker_install_commands(manager, os_profile)
    if requirement.title == "Install Docker Compose":
        return build_docker_compose_install_commands(manager, os_profile)
    if requirement.title == "Start Docker Daemon":
        return build_docker_daemon_commands(os_profile)
    if requirement.title == "Install Git":
        return build_install_commands(manager, ("git",))
    if requirement.title == "Create Virtual Environment":
        return (venv_command("Create project virtual environment", sys.executable, ".venv"),)
    if requirement.title == "Configure Docker Permissions":
        return build_docker_permission_commands()
    if requirement.title == "Create Runtime Directories":
        return build_runtime_directory_commands(scan.missing_runtime_directories)
    if requirement.title == "Build Containers":
        return (
            subprocess_command("Build container images", ("docker", "compose", "build")),
        )
    if requirement.title == "Initialize Runtime":
        return (runtime_init_command("Initialize runtime directories and state"),)
    return ()


def execute_install_plan(
    console: Console,
    plan: DependencyPlan,
    scan: EnvironmentScan,
    *,
    auto_approve_required: bool = False,
    allowed_titles: tuple[str, ...] | None = None,
) -> InstallerRunResult:
    """Execute installer plan with confirmations and rollback."""

    os_profile = detect_os_profile()
    log = create_transaction_log()
    if not os_profile.supported:
        console.print(
            Panel(
                f"Installer unsupported on {os_profile.family} ({os_profile.distribution}).",
                title="Installer Engine",
                border_style="red",
            )
        )
        return InstallerRunResult(applied=(), skipped_requirements=(), failed_requirement="unsupported-os", rollback_results=())

    applied: list[CommandExecutionResult] = []
    applied_commands: list[SystemCommand] = []
    skipped: list[str] = []

    for requirement in plan.requirements:
        if allowed_titles is not None and requirement.title not in allowed_titles:
            skipped.append(requirement.title)
            continue
        commands = commands_for_requirement(requirement, scan, os_profile)
        if not commands:
            continue
        approved_value = True if auto_approve_required else confirm_install(console, f"{requirement.title}. Install automatically?")
        if not approved_value:
            skipped.append(requirement.title)
            continue

        progress = Progress(
            SpinnerColumn(style="bright_cyan"),
            TextColumn(f"[bold white]{requirement.title}[/bold white]"),
            BarColumn(bar_width=24, complete_style="bright_cyan", finished_style="bright_cyan"),
            TextColumn("[bright_cyan]{task.completed}/{task.total}[/bright_cyan]"),
            console=console,
        )
        task_id = progress.add_task(requirement.title, total=len(commands), completed=0)
        console.print(progress)
        for command in commands:
            result = run_system_command(command)
            append_transaction_record(
                log,
                build_transaction_record(
                    requirement.title,
                    command,
                    "success" if result.success else "failed",
                    result.stderr or result.stdout or command.description,
                ),
            )
            if not result.success:
                rollback_results = rollback_commands(tuple(applied_commands))
                console.print(
                    Panel(
                        f"{command.description}\n{result.stderr or result.stdout or 'Command failed.'}",
                        title="Installer Failure",
                        border_style="red",
                    )
                )
                return InstallerRunResult(
                    applied=tuple(applied),
                    skipped_requirements=tuple(skipped),
                    failed_requirement=requirement.title,
                    rollback_results=rollback_results,
                )
            applied.append(result)
            applied_commands.append(command)
            progress.update(task_id, advance=1)
        console.print(
            Panel(
                f"{requirement.title} completed successfully.",
                title="Installer Success",
                border_style="green",
            )
        )
    return InstallerRunResult(
        applied=tuple(applied),
        skipped_requirements=tuple(skipped),
        failed_requirement=None,
        rollback_results=(),
    )

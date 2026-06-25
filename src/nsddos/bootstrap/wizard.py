"""Interactive setup wizard rendering."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from nsddos.bootstrap.installer import execute_install_plan
from nsddos.bootstrap.planner import build_dependency_plan
from nsddos.bootstrap.questions import ask_deployment_profile
from nsddos.bootstrap.setup import collect_environment_scan
from nsddos.bootstrap.state import DependencyPlan, EnvironmentScan, SetupState
from nsddos.bootstrap.terminal import (
    build_footer_line,
    build_operator_chips,
    build_operator_header,
    build_operator_screen,
    create_console,
    section_panel,
    status_text,
)


def _format_gib(value: int) -> str:
    if value <= 0:
        return "Unknown"
    return f"{value / (1024**3):.1f} GiB"


def _scan_table(scan: EnvironmentScan) -> Table:
    table = Table(expand=True, box=None, pad_edge=False)
    table.add_column("Check", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="bright_black")
    table.add_row("OS", status_text("OK"), scan.os_family)
    table.add_row("Python", status_text("OK"), scan.python_version)
    table.add_row(
        "Virtualenv",
        status_text("OK" if scan.virtualenv_active else "WARN"),
        "Active" if scan.virtualenv_active else "Inactive",
    )
    table.add_row(
        "Docker",
        status_text("OK" if scan.docker.installed else "MISSING"),
        "Installed" if scan.docker.installed else "Missing",
    )
    table.add_row(
        "Docker Daemon",
        status_text("OK" if scan.docker_daemon_running else "WARN"),
        "Running" if scan.docker_daemon_running else "Stopped",
    )
    table.add_row(
        "Docker Compose",
        status_text("OK" if scan.docker_compose.installed else "MISSING"),
        "Installed" if scan.docker_compose.installed else "Missing",
    )
    table.add_row(
        "Docker Permissions",
        status_text("OK" if scan.docker_permissions_ready else "WARN"),
        "Ready" if scan.docker_permissions_ready else "Needs configuration",
    )
    table.add_row(
        "Git",
        status_text("OK" if scan.git.installed else "MISSING"),
        "Installed" if scan.git.installed else "Missing",
    )
    table.add_row("Available Memory", status_text("OK"), _format_gib(scan.available_memory_bytes))
    table.add_row("Available Disk", status_text("OK"), _format_gib(scan.available_disk_bytes))
    table.add_row(
        "Runtime Directories",
        status_text("OK" if not scan.missing_runtime_directories else "WARN"),
        "Ready" if not scan.missing_runtime_directories else f"Missing {len(scan.missing_runtime_directories)}",
    )
    table.add_row(
        "Runtime Assets",
        status_text("OK" if scan.runtime_assets_ready else "WARN"),
        scan.runtime_assets_detail,
    )
    return table


def _plan_table(plan: DependencyPlan) -> Table:
    table = Table(expand=True, box=None, pad_edge=False)
    table.add_column("Step", style="bold bright_cyan")
    table.add_column("Action", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="bright_black")
    for requirement in plan.requirements:
        table.add_row(
            requirement.code,
            requirement.title,
            status_text("OK" if not requirement.required else "WARN"),
            requirement.detail,
        )
    return table


def _render_scan_progress(console: Console) -> None:
    progress = Progress(
        SpinnerColumn(style="bright_cyan"),
        TextColumn("[bold white]Step 1[/bold white]"),
        TextColumn("[bright_black]Environment scan[/bright_black]"),
        BarColumn(bar_width=24, complete_style="bright_cyan", finished_style="bright_cyan"),
        TextColumn("[bold bright_cyan]done[/bold bright_cyan]"),
        console=console,
    )
    task_id = progress.add_task("scan", total=1, completed=0)
    progress.update(task_id, completed=1)
    console.print(progress)


def render_setup_wizard(console: Console | None = None) -> SetupState:
    """Run interactive setup wizard."""

    active_console = console or create_console()
    _render_scan_progress(active_console)

    scan = collect_environment_scan()
    active_console.print(
        build_operator_screen(
            Group(
                build_operator_header(
                    "Provisioning Surface",
                    "NSDDOS Setup Console",
                    "Secure environment prep, dependency planning, runtime activation",
                ),
            ),
            Group(
                section_panel("Environment Scan", _scan_table(scan)),
            ),
            Group(
                build_operator_chips(
                    (
                        ("OS", scan.os_family),
                        ("PYTHON", scan.python_version),
                        ("DOCKER", "ONLINE" if scan.docker_daemon_running else "OFFLINE"),
                    )
                ),
            ),
            footer=build_footer_line("Environment scan captured. Select deployment mode to continue."),
        )
    )

    profile = ask_deployment_profile(active_console)
    active_console.print(
        Panel(
            f"[bold white]Selected[/bold white]  [bold bright_cyan]{profile.label}[/bold bright_cyan]\n"
            f"[bright_black]{profile.description}[/bright_black]",
            title="Operator Profile",
            border_style="cyan",
        )
    )

    plan = build_dependency_plan(scan, profile)
    active_console.print(section_panel("Installation Plan", _plan_table(plan)))
    installer_result = execute_install_plan(active_console, plan, scan)

    final_scan = collect_environment_scan()
    final_plan = build_dependency_plan(final_scan, profile)
    summary_lines = [
        f"[bold white]{len(installer_result.applied)} installer commands applied.[/bold white]",
        f"[bright_black]Skipped requirements: {len(installer_result.skipped_requirements)}[/bright_black]",
    ]
    if installer_result.failed_requirement:
        summary_lines.append(f"[bold red]Failed requirement: {installer_result.failed_requirement}[/bold red]")
        summary_lines.append(
            f"[bright_black]Rollback actions: {len(installer_result.rollback_results)}[/bright_black]"
        )
    else:
        summary_lines.append("[bright_black]Provisioning cycle finished without execution failure.[/bright_black]")
    active_console.print(
        Panel(
            "\n".join(summary_lines),
            title="Provisioning Summary",
            border_style="bright_cyan" if not installer_result.failed_requirement else "red",
        )
    )
    return SetupState(scan=final_scan, profile=profile, plan=final_plan)

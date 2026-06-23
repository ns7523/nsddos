"""CLI-facing doctor entrypoint."""

from __future__ import annotations

import typer
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from nsddos.bootstrap.diagnostics_engine import collect_diagnostic_findings
from nsddos.bootstrap.recovery_actions import build_repair_plan
from nsddos.bootstrap.repair_engine import execute_repairs
from nsddos.bootstrap.state import DoctorResult
from nsddos.bootstrap.terminal import (
    build_footer_line,
    build_operator_chips,
    build_operator_header,
    build_operator_screen,
    create_console,
    status_text,
)


def _findings_table(findings):
    table = Table(expand=True, box=None, pad_edge=False)
    table.add_column("Area", style="bold white")
    table.add_column("Check", style="bold bright_cyan")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="bright_black")
    for finding in findings:
        badge = "OK" if finding.status == "pass" else "WARN"
        if finding.status == "fail":
            badge = "MISSING" if finding.repairable else "WARN"
        table.add_row(finding.area, finding.check_name, status_text(badge), finding.detail)
    return table


def _repair_table(actions):
    table = Table(expand=True, box=None, pad_edge=False)
    table.add_column("Area", style="bold white")
    table.add_column("Repair", style="bold bright_cyan")
    table.add_column("Detail", style="bright_black")
    for action in actions:
        table.add_row(action.area, action.title, action.detail)
    return table


def run_doctor_command(console: Console | None = None) -> DoctorResult:
    """Run full doctor + self-healing."""

    active_console = console or create_console()
    findings = collect_diagnostic_findings()
    header = build_operator_header(
        "Recovery Surface",
        "NSDDOS Doctor Console",
        "Critical path diagnostics, repair planning, runtime integrity",
    )
    repairable = sum(1 for finding in findings if finding.repairable)
    critical = sum(1 for finding in findings if finding.critical and finding.status == "fail")
    primary_sections = [
        Panel(_findings_table(findings), title="Diagnostic Feed", border_style="bright_cyan"),
    ]
    plan = build_repair_plan(findings)
    if plan:
        primary_sections.append(Panel(_repair_table(plan), title="Operator Repairs", border_style="yellow"))
    primary = Group(*primary_sections)
    secondary = Group(
        build_operator_chips(
            (
                ("FAILURES", str(sum(1 for finding in findings if finding.status == "fail"))),
                ("CRITICAL", str(critical)),
                ("REPAIRABLE", str(repairable)),
            )
        ),
    )
    active_console.print(
        build_operator_screen(
            header,
            primary,
            secondary,
            footer=build_footer_line("Doctor console engaged. Repairs apply only to explicit operator-safe actions."),
        )
    )
    applied = execute_repairs(active_console, plan)
    rerun_findings = collect_diagnostic_findings() if applied else findings
    unrepaired = tuple(
        f"{finding.area}:{finding.check_name}"
        for finding in rerun_findings
        if finding.status == "fail" and finding.critical
    )
    result = DoctorResult(
        findings=rerun_findings,
        repair_plan=plan,
        applied_repairs=applied,
        unrepaired_failures=unrepaired,
    )
    active_console.print(
        Panel(
            "\n".join(
                [
                    "[bold bright_cyan]Operator Repair Cycle Complete[/bold bright_cyan]",
                    f"[bold white]Applied repairs: {len(applied)}[/bold white]",
                    f"[bright_black]Critical failures remaining: {len(unrepaired)}[/bright_black]",
                ]
            ),
            title="Recovery Summary",
            border_style="red" if unrepaired else "green",
        )
    )
    return result


def ensure_doctor_success(result: DoctorResult) -> None:
    """Raise nonzero exit when critical issues remain."""

    if result.unrepaired_failures:
        raise typer.Exit(code=1)

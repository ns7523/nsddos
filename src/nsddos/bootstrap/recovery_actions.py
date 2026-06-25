"""Repair-action planning from doctor findings."""

from __future__ import annotations

from nsddos.bootstrap.setup import collect_environment_scan
from nsddos.bootstrap.stack import detect_compose_backend, compose_command
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.bootstrap.state import DiagnosticFinding, RepairAction


def build_repair_plan(
    findings: tuple[DiagnosticFinding, ...]
) -> tuple[RepairAction, ...]:
    """Build repair actions from findings."""

    actions: list[RepairAction] = []
    by_check = {
        finding.check_name: finding for finding in findings if finding.status == "fail"
    }
    scan = collect_environment_scan()

    if any(
        name in by_check
        for name in ("docker", "docker_daemon", "docker_permissions", "compose")
    ):
        actions.append(
            RepairAction(
                area="docker",
                title="Repair Docker Prerequisites",
                detail="Run installer subset for Docker, compose, daemon, permissions, runtime dirs.",
                action_type="installer",
            )
        )
    if any(
        finding.area == "containers" and finding.status == "fail"
        for finding in findings
    ):
        backend = detect_compose_backend()
        command = (
            compose_command(backend, ("up", "-d", "--build"))
            if backend is not None
            else ()
        )
        actions.append(
            RepairAction(
                area="containers",
                title="Repair Containers",
                detail="Rebuild and restart compose stack.",
                action_type="container_repair",
                command=command,
            )
        )
    if any(
        finding.area == "runtime" and finding.status == "fail" for finding in findings
    ):
        actions.append(
            RepairAction(
                area="runtime",
                title="Repair Runtime State",
                detail="Reinitialize runtime directories and state scaffolding.",
                action_type="runtime_repair",
            )
        )
    if by_check.get("ui_reachable") is not None:
        actions.append(
            RepairAction(
                area="ui",
                title="Restart UI",
                detail=f"Restart UI server on {DEFAULT_STARTUP_PROFILE.ui_url}.",
                action_type="ui_restart",
            )
        )
    if by_check.get("session_file") is not None:
        actions.append(
            RepairAction(
                area="session",
                title="Recreate Session",
                detail="Regenerate session.json from current stack state.",
                action_type="session_repair",
            )
        )
    if by_check.get("venv") is not None and not scan.virtualenv_active:
        actions.append(
            RepairAction(
                area="environment",
                title="Create Virtual Environment",
                detail="Create local project virtual environment.",
                action_type="venv_repair",
            )
        )
    if by_check.get("git") is not None:
        actions.append(
            RepairAction(
                area="environment",
                title="Install Git",
                detail="Install Git using installer subsystem.",
                action_type="git_repair",
            )
        )
    seen: set[str] = set()
    unique: list[RepairAction] = []
    for action in actions:
        if action.title in seen:
            continue
        seen.add(action.title)
        unique.append(action)
    return tuple(unique)

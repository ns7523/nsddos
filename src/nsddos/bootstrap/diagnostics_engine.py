"""Diagnostic sweep for doctor command."""

from __future__ import annotations

from nsddos.bootstrap.orchestrator import load_startup_session
from nsddos.bootstrap.service_monitor import parse_compose_ps_output
from nsddos.bootstrap.setup import collect_environment_scan
from nsddos.bootstrap.stack import (
    detect_compose_backend,
    list_stack_services,
    run_compose_command,
)
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.bootstrap.state import DiagnosticFinding
from nsddos.bootstrap.ui_launcher import ui_reachable
from nsddos.health_checks import collect_runtime_health


def _restart_loop_names(raw: str) -> tuple[str, ...]:
    services = parse_compose_ps_output(raw)
    offenders: list[str] = []
    for service in services:
        text = f"{service.state} {service.health}".lower()
        if "restarting" in text or "restart" in text:
            offenders.append(service.container_name)
    return tuple(offenders)


def collect_diagnostic_findings() -> tuple[DiagnosticFinding, ...]:
    """Collect doctor findings."""

    scan = collect_environment_scan()
    findings: list[DiagnosticFinding] = [
        DiagnosticFinding(
            "environment", "python", "pass", scan.python_version, repairable=False
        ),
        DiagnosticFinding(
            "environment",
            "venv",
            "pass" if scan.virtualenv_active else "fail",
            "Active" if scan.virtualenv_active else "Inactive",
            repairable=not scan.virtualenv_active,
            critical=not scan.virtualenv_active,
        ),
        DiagnosticFinding(
            "environment",
            "git",
            "pass" if scan.git.installed else "fail",
            "Installed" if scan.git.installed else "Missing",
            repairable=not scan.git.installed,
            critical=not scan.git.installed,
        ),
        DiagnosticFinding(
            "docker",
            "docker",
            "pass" if scan.docker.installed else "fail",
            "Installed" if scan.docker.installed else "Missing",
            repairable=not scan.docker.installed,
            critical=not scan.docker.installed,
        ),
        DiagnosticFinding(
            "docker",
            "docker_daemon",
            "pass" if scan.docker_daemon_running else "fail",
            "Running" if scan.docker_daemon_running else "Stopped",
            repairable=not scan.docker_daemon_running,
            critical=not scan.docker_daemon_running,
        ),
        DiagnosticFinding(
            "docker",
            "docker_permissions",
            "pass" if scan.docker_permissions_ready else "fail",
            "Ready" if scan.docker_permissions_ready else "Broken",
            repairable=not scan.docker_permissions_ready,
            critical=not scan.docker_permissions_ready,
        ),
        DiagnosticFinding(
            "docker",
            "compose",
            "pass" if scan.docker_compose.installed else "fail",
            "Installed" if scan.docker_compose.installed else "Missing",
            repairable=not scan.docker_compose.installed,
            critical=not scan.docker_compose.installed,
        ),
    ]

    backend = detect_compose_backend()
    services = list_stack_services(backend) if backend is not None else ()
    service_by_name = {service.container_name: service for service in services}
    restart_loops = ()
    if backend is not None:
        ps_result = run_compose_command(backend, ("ps", "--format", "json"))
        if ps_result.returncode == 0:
            restart_loops = _restart_loop_names(ps_result.stdout.strip())

    for container_name in DEFAULT_STARTUP_PROFILE.container_names:
        service = service_by_name.get(container_name)
        if service is None:
            findings.append(
                DiagnosticFinding(
                    "containers",
                    container_name,
                    "fail",
                    "Missing",
                    repairable=True,
                    critical=True,
                )
            )
            continue
        findings.append(
            DiagnosticFinding(
                "containers",
                f"{container_name}:exists",
                "pass",
                service.container_id or "present",
                repairable=False,
            )
        )
        findings.append(
            DiagnosticFinding(
                "containers",
                f"{container_name}:running",
                "pass" if service.state.lower() == "running" else "fail",
                service.state,
                repairable=service.state.lower() != "running",
                critical=service.state.lower() != "running",
            )
        )
        findings.append(
            DiagnosticFinding(
                "containers",
                f"{container_name}:healthy",
                "pass" if service.healthy else "fail",
                service.health,
                repairable=not service.healthy,
                critical=not service.healthy,
            )
        )
        findings.append(
            DiagnosticFinding(
                "containers",
                f"{container_name}:restart_loop",
                "fail" if container_name in restart_loops else "pass",
                (
                    "Restart loop suspected"
                    if container_name in restart_loops
                    else "Stable"
                ),
                repairable=container_name in restart_loops,
                critical=container_name in restart_loops,
            )
        )

    runtime_results = tuple(collect_runtime_health())
    for result in runtime_results:
        findings.append(
            DiagnosticFinding(
                "runtime",
                result.name,
                "pass" if result.ok else "fail",
                result.detail,
                repairable=not result.ok,
                critical=not result.ok,
            )
        )

    ui_ok = ui_reachable(DEFAULT_STARTUP_PROFILE.ui_url)
    findings.append(
        DiagnosticFinding(
            "ui",
            "ui_reachable",
            "pass" if ui_ok else "fail",
            DEFAULT_STARTUP_PROFILE.ui_url,
            repairable=not ui_ok,
            critical=not ui_ok,
        )
    )

    session_path = DEFAULT_STARTUP_PROFILE.session_path
    if not session_path.exists():
        findings.append(
            DiagnosticFinding(
                "session",
                "session_file",
                "fail",
                "Missing",
                repairable=True,
                critical=False,
            )
        )
    else:
        session = load_startup_session(session_path)
        if session is None or not session.ui_url or not session.started_at:
            findings.append(
                DiagnosticFinding(
                    "session",
                    "session_file",
                    "fail",
                    "Corrupt",
                    repairable=True,
                    critical=False,
                )
            )
        else:
            findings.append(
                DiagnosticFinding(
                    "session",
                    "session_file",
                    "pass",
                    str(session_path),
                    repairable=False,
                )
            )

    return tuple(findings)

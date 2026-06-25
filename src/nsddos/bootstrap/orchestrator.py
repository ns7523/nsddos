"""One-command startup orchestration."""

from __future__ import annotations

from collections.abc import Callable
import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from nsddos.bootstrap.healthwait import wait_for_stack_health
from nsddos.bootstrap.runtime_boot import (
    ensure_startup_prerequisites,
    validate_runtime_health,
)
from nsddos.bootstrap.stack import (
    detect_compose_backend,
    list_stack_services,
    stack_has_required_services,
    stack_is_healthy,
    start_stack,
)
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.bootstrap.state import StartupPortBinding, StartupResult, StartupSession
from nsddos.bootstrap.ui_launcher import launch_ui_background, ui_reachable
from nsddos.runtime.persistence import atomic_write_json


def load_startup_session(path: Path | None = None) -> StartupSession | None:
    """Load persisted startup session if present."""

    target_path = path or DEFAULT_STARTUP_PROFILE.session_path
    if not target_path.exists():
        return None
    try:
        payload = json.loads(target_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return StartupSession.from_dict(payload)


def persist_startup_session(session: StartupSession, path: Path | None = None) -> Path:
    """Persist startup session."""

    target_path = path or DEFAULT_STARTUP_PROFILE.session_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(target_path, session.to_dict())
    return target_path


def build_startup_session(
    running_containers: tuple[str, ...],
    health_state: str,
    ui_url: str,
) -> StartupSession:
    """Build typed startup session."""

    return StartupSession(
        started_at=datetime.now(timezone.utc).isoformat(),
        running_containers=running_containers,
        ports=(
            StartupPortBinding(name="ui", port=DEFAULT_STARTUP_PROFILE.ui_port),
            StartupPortBinding(name="floodlight", port=8080),
            StartupPortBinding(name="sflowrt", port=8008),
            StartupPortBinding(name="detector", port=9000),
        ),
        health_state=health_state,
        ui_url=ui_url,
    )


def _notify(
    callback: Callable[[str, str, str], None] | None,
    step: str,
    status: str,
    detail: str,
) -> None:
    """Emit startup stage update when callback is configured."""

    if callback is not None:
        callback(step, status, detail)


def orchestrate_startup(
    console: Console,
    status_callback: Callable[[str, str, str], None] | None = None,
) -> StartupResult:
    """Run startup orchestration."""

    _notify(
        status_callback, "environment", "pending", "Validating runtime prerequisites"
    )
    scan, installer_result = ensure_startup_prerequisites(console)
    if installer_result.failed_requirement:
        _notify(
            status_callback, "environment", "fail", installer_result.failed_requirement
        )
        return StartupResult(
            already_running=False,
            stack_started=False,
            runtime_valid=False,
            ui_launched=False,
            ui_url=DEFAULT_STARTUP_PROFILE.ui_url,
            failed_checks=(installer_result.failed_requirement,),
        )
    _notify(
        status_callback,
        "environment",
        "ok",
        f"{scan.os_family} / Python {scan.python_version}",
    )

    _notify(status_callback, "compose", "pending", "Connecting Docker Compose backend")
    backend = detect_compose_backend()
    if backend is None:
        _notify(status_callback, "compose", "fail", "Compose backend unavailable")
        return StartupResult(
            already_running=False,
            stack_started=False,
            runtime_valid=False,
            ui_launched=False,
            ui_url=DEFAULT_STARTUP_PROFILE.ui_url,
            failed_checks=("compose-backend",),
        )
    _notify(status_callback, "compose", "ok", backend.name)

    current_services = list_stack_services(backend)
    existing_session = load_startup_session()
    session_url = (
        existing_session.ui_url
        if existing_session is not None
        else DEFAULT_STARTUP_PROFILE.ui_url
    )
    if stack_is_healthy(
        current_services, DEFAULT_STARTUP_PROFILE.container_names
    ) and ui_reachable(session_url):
        _notify(status_callback, "stack", "ok", "Runtime containers already healthy")
        _notify(status_callback, "services", "ok", "Service fabric already healthy")
        _, failures = validate_runtime_health()
        if not failures:
            _notify(
                status_callback,
                "runtime",
                "ok",
                "Controller, telemetry, helper runtime validated",
            )
            session = build_startup_session(
                tuple(service.container_name for service in current_services),
                "healthy",
                session_url,
            )
            persist_startup_session(session)
            _notify(status_callback, "ui", "ok", session_url)
            return StartupResult(
                already_running=True,
                stack_started=False,
                runtime_valid=True,
                ui_launched=False,
                ui_url=session_url,
                failed_checks=(),
                session=session,
            )

    stack_started = False
    if not stack_has_required_services(
        current_services, DEFAULT_STARTUP_PROFILE.container_names
    ):
        _notify(
            status_callback, "stack", "pending", "Building and starting runtime fabric"
        )
        start_result = start_stack(backend, rebuild=True)
        if start_result.returncode != 0:
            _notify(status_callback, "stack", "fail", "Compose startup failed")
            console.print(
                Panel(
                    start_result.stderr
                    or start_result.stdout
                    or "Compose startup failed.",
                    title="Stack Start Failure",
                    border_style="red",
                )
            )
            return StartupResult(
                already_running=False,
                stack_started=False,
                runtime_valid=False,
                ui_launched=False,
                ui_url=DEFAULT_STARTUP_PROFILE.ui_url,
                failed_checks=("compose-up",),
            )
        stack_started = True
        _notify(status_callback, "stack", "ok", "Runtime fabric online")
    else:
        _notify(status_callback, "stack", "ok", "Required containers already present")

    try:
        wait_result = wait_for_stack_health(
            console,
            backend,
            render_progress=status_callback is None,
            status_callback=status_callback,
        )
    except TypeError:
        wait_result = wait_for_stack_health(console, backend)
    if not wait_result.success:
        _notify(
            status_callback, "services", "fail", ", ".join(wait_result.pending_services)
        )
        return StartupResult(
            already_running=False,
            stack_started=stack_started,
            runtime_valid=False,
            ui_launched=False,
            ui_url=DEFAULT_STARTUP_PROFILE.ui_url,
            failed_checks=wait_result.pending_services,
        )

    _notify(
        status_callback,
        "services",
        "ok",
        "Floodlight, sFlowRT, labhost, detector healthy",
    )
    _, failures = validate_runtime_health()
    if failures:
        _notify(status_callback, "runtime", "fail", ", ".join(failures))
        return StartupResult(
            already_running=False,
            stack_started=stack_started,
            runtime_valid=False,
            ui_launched=False,
            ui_url=DEFAULT_STARTUP_PROFILE.ui_url,
            failed_checks=failures,
        )
    _notify(
        status_callback,
        "runtime",
        "ok",
        "Controller, telemetry, Mininet, OVS validated",
    )

    _notify(status_callback, "ui", "pending", "Launching operator command center")
    ui_result = launch_ui_background()
    if not ui_result.reachable:
        _notify(status_callback, "ui", "fail", ui_result.ui_url)
        return StartupResult(
            already_running=False,
            stack_started=stack_started,
            runtime_valid=True,
            ui_launched=ui_result.launched,
            ui_url=ui_result.ui_url,
            failed_checks=("ui",),
        )
    _notify(status_callback, "ui", "ok", ui_result.ui_url)

    running_containers = tuple(
        service.container_name
        for service in wait_result.services
        if service.container_name
    )
    session = build_startup_session(running_containers, "healthy", ui_result.ui_url)
    persist_startup_session(session)
    return StartupResult(
        already_running=False,
        stack_started=stack_started,
        runtime_valid=True,
        ui_launched=ui_result.launched,
        ui_url=ui_result.ui_url,
        failed_checks=(),
        session=session,
    )

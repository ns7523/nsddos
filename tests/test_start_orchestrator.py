"""Tests for one-command startup orchestration."""

from __future__ import annotations

import subprocess
from pathlib import Path

from nsddos.bootstrap.healthwait import wait_for_stack_health
from nsddos.bootstrap.orchestrator import load_startup_session, orchestrate_startup
from nsddos.bootstrap.runtime_boot import ensure_startup_prerequisites, validate_runtime_health
from nsddos.bootstrap.start import run_startup_command
from nsddos.bootstrap.stack import detect_compose_backend
from nsddos.bootstrap.startup_profiles import StartupProfile
from nsddos.bootstrap.state import (
    ComposeBackend,
    DependencyPlan,
    DeploymentProfile,
    EnvironmentScan,
    StartupServiceStatus,
    ToolStatus,
    UILaunchResult,
)
from nsddos.bootstrap.terminal import create_console
from nsddos.runtime.models import HealthResult


def _scan(**overrides) -> EnvironmentScan:
    payload = {
        "os_name": "Linux",
        "os_family": "Linux",
        "python_version": "3.11.9",
        "virtualenv_active": True,
        "docker": ToolStatus(name="docker", installed=True, detail="/usr/bin/docker"),
        "docker_daemon_running": True,
        "docker_compose": ToolStatus(name="docker-compose", installed=True, detail="docker compose"),
        "docker_permissions_ready": True,
        "git": ToolStatus(name="git", installed=True, detail="/usr/bin/git"),
        "available_memory_bytes": 16 * 1024**3,
        "available_disk_bytes": 40 * 1024**3,
        "missing_runtime_directories": (),
    }
    payload.update(overrides)
    return EnvironmentScan(**payload)


def _healthy_services() -> tuple[StartupServiceStatus, ...]:
    return (
        StartupServiceStatus("labhost", "nsddos-labhost", "running", "healthy", True, "1"),
        StartupServiceStatus("floodlight", "nsddos-floodlight", "running", "healthy", True, "2"),
        StartupServiceStatus("sflowrt", "nsddos-sflowrt", "running", "healthy", True, "3"),
        StartupServiceStatus("detector", "nsddos-detector", "running", "healthy", True, "4"),
    )


def test_detect_compose_backend_prefers_docker_compose(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.bootstrap.stack.resolve_compose_command", lambda: ("docker", "compose"))

    backend = detect_compose_backend()

    assert backend == ComposeBackend(name="docker-compose-v2", command=("docker", "compose"))


def test_detect_compose_backend_falls_back_to_docker_compose_binary(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.bootstrap.stack.resolve_compose_command", lambda: ("docker-compose",))

    backend = detect_compose_backend()

    assert backend == ComposeBackend(name="docker-compose-v1", command=("docker-compose",))


def test_ensure_startup_prerequisites_uses_installer_subset(monkeypatch) -> None:
    initial_scan = _scan(docker_daemon_running=False, docker_compose=ToolStatus(name="docker-compose", installed=False, detail=None))
    final_scan = _scan()
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        "nsddos.bootstrap.runtime_boot.collect_environment_scan",
        lambda: initial_scan if "first" not in calls else final_scan,
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.runtime_boot.build_dependency_plan",
        lambda scan, profile: DependencyPlan(
            profile=DeploymentProfile("local-development", "Local Development", "dev"),
            requirements=(),
            summary="startup",
        ),
    )

    def fake_execute(console, plan, scan, **kwargs):
        calls["first"] = True
        calls["kwargs"] = kwargs
        return type(
            "InstallerResult",
            (),
            {
                "applied": (),
                "skipped_requirements": (),
                "failed_requirement": None,
                "rollback_results": (),
            },
        )()

    monkeypatch.setattr("nsddos.bootstrap.runtime_boot.execute_install_plan", fake_execute)

    scan, _ = ensure_startup_prerequisites(create_console(record=True))

    assert scan == final_scan
    assert calls["kwargs"] == {
        "auto_approve_required": True,
        "allowed_titles": (
            "Install Docker",
            "Install Docker Compose",
            "Start Docker Daemon",
            "Configure Docker Permissions",
            "Create Runtime Directories",
        ),
    }


def test_validate_runtime_health_prefers_helper_container_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        "nsddos.bootstrap.runtime_boot.collect_runtime_health",
        lambda: [
            HealthResult("docker_daemon", True, "docker daemon reachable", "runtime"),
            HealthResult("containers", True, "all healthy", "runtime"),
            HealthResult("floodlight", True, "http://127.0.0.1:8080", "runtime"),
            HealthResult("sflowrt", True, "http://127.0.0.1:8008", "runtime"),
            HealthResult("mininet", False, "legacy topology not started", "runtime"),
            HealthResult("ovs", False, "legacy host ovs missing", "runtime"),
        ],
    )
    monkeypatch.setattr("nsddos.bootstrap.runtime_boot.helper_running", lambda: True)

    def _helper_exec(args, timeout=10):
        if args == ["mn", "--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="2.3.0\n", stderr="")
        if args == ["ovs-vsctl", "show"]:
            return subprocess.CompletedProcess(args, 0, stdout="Bridge s1\n", stderr="")
        raise AssertionError(f"unexpected helper command: {args}")

    monkeypatch.setattr("nsddos.bootstrap.runtime_boot.helper_exec", _helper_exec)

    results, failures = validate_runtime_health()
    by_name = {result.name: result for result in results}

    assert failures == ()
    assert by_name["mininet"].ok is True
    assert by_name["ovs"].ok is True
    assert by_name["mininet"].detail == "2.3.0"
    assert by_name["ovs"].detail == "Bridge s1"


def test_validate_runtime_health_reports_helper_internal_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        "nsddos.bootstrap.runtime_boot.collect_runtime_health",
        lambda: [
            HealthResult("docker_daemon", True, "docker daemon reachable", "runtime"),
            HealthResult("containers", True, "all healthy", "runtime"),
            HealthResult("floodlight", True, "http://127.0.0.1:8080", "runtime"),
            HealthResult("sflowrt", True, "http://127.0.0.1:8008", "runtime"),
        ],
    )
    monkeypatch.setattr("nsddos.bootstrap.runtime_boot.helper_running", lambda: True)

    def _helper_exec(args, timeout=10):
        if args == ["mn", "--version"]:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="mn missing")
        if args == ["ovs-vsctl", "show"]:
            return subprocess.CompletedProcess(args, 0, stdout="Bridge s1\n", stderr="")
        raise AssertionError(f"unexpected helper command: {args}")

    monkeypatch.setattr("nsddos.bootstrap.runtime_boot.helper_exec", _helper_exec)

    results, failures = validate_runtime_health()
    by_name = {result.name: result for result in results}

    assert failures == ("mininet",)
    assert by_name["mininet"].ok is False
    assert by_name["mininet"].detail == "mn missing"


def test_wait_for_stack_health_times_out_with_pending_services(monkeypatch) -> None:
    services = (
        StartupServiceStatus("labhost", "nsddos-labhost", "running", "healthy", True, "1"),
    )
    values = [0.0, 0.0, 1.0, 1.0, 2.1]
    state = {"index": 0}
    def fake_monotonic() -> float:
        index = state["index"]
        if index >= len(values):
            return values[-1]
        state["index"] = index + 1
        return values[index]
    monkeypatch.setattr("nsddos.bootstrap.healthwait.list_stack_services", lambda backend: services)
    monkeypatch.setattr("nsddos.bootstrap.healthwait.time.sleep", lambda *_args: None)
    monkeypatch.setattr("nsddos.bootstrap.healthwait.time.monotonic", fake_monotonic)

    result = wait_for_stack_health(
        create_console(record=True),
        ComposeBackend(name="docker-compose-v2", command=("docker", "compose")),
        timeout_seconds=2,
        poll_interval_seconds=1,
    )

    assert result.success is False
    assert "nsddos-floodlight" in result.pending_services


def test_orchestrator_detects_already_running_and_persists_session(monkeypatch, tmp_path) -> None:
    profile = StartupProfile(
        container_names=("nsddos-labhost", "nsddos-floodlight", "nsddos-sflowrt", "nsddos-detector"),
        required_health_checks=("docker_daemon", "containers"),
        ui_host="127.0.0.1",
        ui_port=8010,
        health_timeout_seconds=90,
        health_poll_interval_seconds=2,
        session_path=tmp_path / "session.json",
    )
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.DEFAULT_STARTUP_PROFILE", profile)
    monkeypatch.setattr(
        "nsddos.bootstrap.orchestrator.ensure_startup_prerequisites",
        lambda console: (
            _scan(),
            type("InstallerResult", (), {"failed_requirement": None, "applied": (), "skipped_requirements": (), "rollback_results": ()})(),
        ),
    )
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.detect_compose_backend", lambda: ComposeBackend("docker-compose-v2", ("docker", "compose")))
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.list_stack_services", lambda backend: _healthy_services())
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.ui_reachable", lambda url: True)
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.validate_runtime_health", lambda: ((), ()))
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.launch_ui_background", lambda: (_ for _ in ()).throw(AssertionError("should not launch ui")))

    result = orchestrate_startup(create_console(record=True))

    assert result.already_running is True
    assert result.session is not None
    assert Path(profile.session_path).exists()
    session = load_startup_session(profile.session_path)
    assert session is not None
    assert session.ui_url == profile.ui_url


def test_orchestrator_persists_successful_startup_session(monkeypatch, tmp_path) -> None:
    profile = StartupProfile(
        container_names=("nsddos-labhost", "nsddos-floodlight", "nsddos-sflowrt", "nsddos-detector"),
        required_health_checks=("docker_daemon", "containers"),
        ui_host="127.0.0.1",
        ui_port=8010,
        health_timeout_seconds=90,
        health_poll_interval_seconds=2,
        session_path=tmp_path / "session.json",
    )
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.DEFAULT_STARTUP_PROFILE", profile)
    monkeypatch.setattr(
        "nsddos.bootstrap.orchestrator.ensure_startup_prerequisites",
        lambda console: (
            _scan(),
            type("InstallerResult", (), {"failed_requirement": None, "applied": (), "skipped_requirements": (), "rollback_results": ()})(),
        ),
    )
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.detect_compose_backend", lambda: ComposeBackend("docker-compose-v2", ("docker", "compose")))
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.list_stack_services", lambda backend: ())
    monkeypatch.setattr(
        "nsddos.bootstrap.orchestrator.start_stack",
        lambda backend, rebuild: subprocess.CompletedProcess(["docker"], 0, stdout="started", stderr=""),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.orchestrator.wait_for_stack_health",
        lambda console, backend: type(
            "WaitResult",
            (),
            {
                "success": True,
                "timed_out": False,
                "pending_services": (),
                "services": _healthy_services(),
            },
        )(),
    )
    monkeypatch.setattr("nsddos.bootstrap.orchestrator.validate_runtime_health", lambda: ((), ()))
    monkeypatch.setattr(
        "nsddos.bootstrap.orchestrator.launch_ui_background",
        lambda: UILaunchResult(launched=True, reachable=True, ui_url=profile.ui_url),
    )

    result = orchestrate_startup(create_console(record=True))

    assert result.already_running is False
    assert result.stack_started is True
    assert result.ui_launched is True
    assert result.session is not None
    assert Path(profile.session_path).exists()


def test_run_startup_command_renders_boot_monitor_without_panel_matrix(monkeypatch) -> None:
    console = create_console(record=True)

    def fake_orchestrate(_console, status_callback=None):
        if status_callback is not None:
            status_callback("environment", "ok", "env ready")
            status_callback("compose", "ok", "compose ready")
            status_callback("stack", "ok", "stack ready")
            status_callback("services", "ok", "services ready")
            status_callback("runtime", "ok", "runtime ready")
            status_callback("ui", "ok", "ui ready")
        return type("Result", (), {"failed_checks": (), "ui_url": "http://127.0.0.1:8010"})()

    monkeypatch.setattr("nsddos.bootstrap.start.orchestrate_startup", fake_orchestrate)

    result = run_startup_command(console)
    output = console.export_text()

    assert result.ui_url == "http://127.0.0.1:8010"
    assert "BOOT LOG" in output
    assert "SERVICE BRING-UP" in output
    assert "NSDDOS" in output
    assert "Runtime Phase Matrix" not in output
    assert "Command Center" not in output

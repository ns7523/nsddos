"""Tests for doctor diagnostics, repairs, and reset."""

from __future__ import annotations

import subprocess

from typer.testing import CliRunner

from nsddos.bootstrap.diagnostics_engine import collect_diagnostic_findings
from nsddos.bootstrap.doctor import run_doctor_command
from nsddos.bootstrap.recovery_actions import build_repair_plan
from nsddos.bootstrap.repair_engine import execute_repairs
from nsddos.bootstrap.reset_engine import execute_reset
from nsddos.bootstrap.startup_profiles import StartupProfile
from nsddos.bootstrap.state import (
    ComposeBackend,
    DiagnosticFinding,
    DoctorResult,
    EnvironmentScan,
    ResetResult,
    StartupServiceStatus,
    StartupSession,
    ToolStatus,
    UILaunchResult,
)
from nsddos.bootstrap.terminal import create_console
from nsddos.cli import app
from nsddos.runtime.models import HealthResult


def _scan(**overrides) -> EnvironmentScan:
    payload = {
        "os_name": "Linux",
        "os_family": "Linux",
        "python_version": "3.11.9",
        "virtualenv_active": True,
        "docker": ToolStatus(name="docker", installed=True, detail="/usr/bin/docker"),
        "docker_daemon_running": True,
        "docker_compose": ToolStatus(
            name="docker-compose", installed=True, detail="docker compose"
        ),
        "docker_permissions_ready": True,
        "git": ToolStatus(name="git", installed=True, detail="/usr/bin/git"),
        "available_memory_bytes": 16 * 1024**3,
        "available_disk_bytes": 40 * 1024**3,
        "missing_runtime_directories": (),
        "runtime_assets_ready": True,
        "runtime_assets_source": "repo",
        "runtime_assets_detail": "repository runtime payloads available",
    }
    payload.update(overrides)
    return EnvironmentScan(**payload)


def _healthy_services() -> tuple[StartupServiceStatus, ...]:
    return (
        StartupServiceStatus(
            "floodlight", "nsddos-floodlight", "running", "healthy", True, "1"
        ),
        StartupServiceStatus(
            "sflowrt", "nsddos-sflowrt", "running", "healthy", True, "2"
        ),
        StartupServiceStatus(
            "labhost", "nsddos-labhost", "running", "healthy", True, "3"
        ),
        StartupServiceStatus(
            "detector", "nsddos-detector", "running", "healthy", True, "4"
        ),
    )


def test_collect_diagnostic_findings_detects_failures(monkeypatch, tmp_path) -> None:
    profile = StartupProfile(
        container_names=(
            "nsddos-floodlight",
            "nsddos-sflowrt",
            "nsddos-labhost",
            "nsddos-detector",
        ),
        required_health_checks=("docker_daemon", "containers"),
        ui_host="127.0.0.1",
        ui_port=8010,
        health_timeout_seconds=90,
        health_poll_interval_seconds=2,
        session_path=tmp_path / "session.json",
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.collect_environment_scan",
        lambda: _scan(
            virtualenv_active=False,
            docker=ToolStatus(name="docker", installed=False, detail=None),
            docker_daemon_running=False,
            docker_compose=ToolStatus(
                name="docker-compose", installed=False, detail=None
            ),
            docker_permissions_ready=False,
            git=ToolStatus(name="git", installed=False, detail=None),
        ),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.DEFAULT_STARTUP_PROFILE", profile
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.detect_compose_backend", lambda: None
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.ui_reachable", lambda _url: False
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.collect_runtime_health",
        lambda: [HealthResult("floodlight", False, "missing", "runtime")],
    )

    findings = collect_diagnostic_findings()
    by_name = {(item.area, item.check_name): item for item in findings}

    assert by_name[("environment", "venv")].status == "fail"
    assert by_name[("docker", "docker")].status == "fail"
    assert by_name[("docker", "compose")].status == "fail"
    assert by_name[("runtime", "floodlight")].detail == "missing"
    assert by_name[("ui", "ui_reachable")].status == "fail"
    assert by_name[("session", "session_file")].detail == "Missing"


def test_collect_diagnostic_findings_detects_corrupt_session(
    monkeypatch, tmp_path
) -> None:
    profile = StartupProfile(
        container_names=(
            "nsddos-floodlight",
            "nsddos-sflowrt",
            "nsddos-labhost",
            "nsddos-detector",
        ),
        required_health_checks=("docker_daemon", "containers"),
        ui_host="127.0.0.1",
        ui_port=8010,
        health_timeout_seconds=90,
        health_poll_interval_seconds=2,
        session_path=tmp_path / "session.json",
    )
    profile.session_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.collect_environment_scan", lambda: _scan()
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.DEFAULT_STARTUP_PROFILE", profile
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.detect_compose_backend",
        lambda: ComposeBackend("docker-compose-v2", ("docker", "compose")),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.list_stack_services",
        lambda _backend: _healthy_services(),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.run_compose_command",
        lambda _backend, _args: subprocess.CompletedProcess(
            _args, 0, stdout="[]", stderr=""
        ),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.collect_runtime_health", lambda: []
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.diagnostics_engine.ui_reachable", lambda _url: True
    )

    findings = collect_diagnostic_findings()
    session_finding = next(item for item in findings if item.area == "session")

    assert session_finding.status == "fail"
    assert session_finding.detail == "Corrupt"


def test_build_repair_plan_maps_findings(monkeypatch) -> None:
    monkeypatch.setattr(
        "nsddos.bootstrap.recovery_actions.collect_environment_scan",
        lambda: _scan(virtualenv_active=False),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.recovery_actions.detect_compose_backend",
        lambda: ComposeBackend("docker-compose-v2", ("docker", "compose")),
    )
    findings = (
        DiagnosticFinding(
            "docker", "docker_daemon", "fail", "Stopped", repairable=True, critical=True
        ),
        DiagnosticFinding(
            "containers",
            "nsddos-floodlight:healthy",
            "fail",
            "unhealthy",
            repairable=True,
            critical=True,
        ),
        DiagnosticFinding(
            "runtime", "ovs", "fail", "missing", repairable=True, critical=True
        ),
        DiagnosticFinding(
            "ui", "ui_reachable", "fail", "down", repairable=True, critical=True
        ),
        DiagnosticFinding(
            "session",
            "session_file",
            "fail",
            "Corrupt",
            repairable=True,
            critical=False,
        ),
        DiagnosticFinding(
            "environment", "venv", "fail", "Inactive", repairable=True, critical=True
        ),
        DiagnosticFinding(
            "environment", "git", "fail", "Missing", repairable=True, critical=True
        ),
    )

    actions = build_repair_plan(findings)
    titles = {item.title for item in actions}

    assert titles == {
        "Repair Docker Prerequisites",
        "Repair Containers",
        "Repair Runtime State",
        "Restart UI",
        "Recreate Session",
        "Create Virtual Environment",
        "Install Git",
    }


def test_execute_repairs_routes_actions(monkeypatch) -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        "nsddos.bootstrap.recovery_actions.collect_environment_scan",
        lambda: _scan(virtualenv_active=False),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.recovery_actions.detect_compose_backend",
        lambda: ComposeBackend("docker-compose-v2", ("docker", "compose")),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.repair_engine.confirm_install", lambda console, prompt: True
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.repair_engine.collect_environment_scan", lambda: _scan()
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.repair_engine.build_dependency_plan",
        lambda scan, profile: type(
            "Plan", (), {"requirements": (), "profile": profile, "summary": "repairs"}
        )(),
    )

    def fake_install(console, plan, scan, **kwargs):
        calls.append(("installer", tuple(kwargs.get("allowed_titles", ()))))
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

    monkeypatch.setattr(
        "nsddos.bootstrap.repair_engine.execute_install_plan", fake_install
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.repair_engine.repair_containers", lambda console: True
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.repair_engine.repair_runtime_state",
        lambda: ("runtime_dirs", "state"),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.repair_engine.launch_ui_background",
        lambda: UILaunchResult(
            launched=True, reachable=True, ui_url="http://127.0.0.1:8010"
        ),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.repair_engine.recreate_startup_session",
        lambda: StartupSession("now", (), (), "healthy", "http://127.0.0.1:8010"),
    )

    actions = (
        DiagnosticFinding("docker", "docker_daemon", "fail", "Stopped", True, True),
        DiagnosticFinding(
            "containers", "nsddos-floodlight:healthy", "fail", "unhealthy", True, True
        ),
        DiagnosticFinding("runtime", "ovs", "fail", "missing", True, True),
        DiagnosticFinding("ui", "ui_reachable", "fail", "down", True, True),
        DiagnosticFinding("session", "session_file", "fail", "Corrupt", True, False),
        DiagnosticFinding("environment", "venv", "fail", "Inactive", True, True),
        DiagnosticFinding("environment", "git", "fail", "Missing", True, True),
    )
    plan = build_repair_plan(actions)

    applied = execute_repairs(create_console(record=True), plan)

    assert applied == tuple(item.title for item in plan)
    assert (
        "installer",
        (
            "Install Docker",
            "Install Docker Compose",
            "Start Docker Daemon",
            "Configure Docker Permissions",
            "Create Runtime Directories",
            "Download Runtime Assets",
            "Install Git",
        ),
    ) in calls
    assert ("installer", ("Create Virtual Environment",)) in calls
    assert ("installer", ("Install Git",)) in calls


def test_execute_reset_preserves_config_and_cleans_state(monkeypatch, tmp_path) -> None:
    runtime_dir = tmp_path / "runtime"
    logs_dir = tmp_path / "logs"
    session_path = tmp_path / "session.json"
    config_path = tmp_path / "config.yaml"
    runtime_dir.mkdir()
    logs_dir.mkdir()
    session_path.write_text("{}", encoding="utf-8")
    config_path.write_text("name: nsddos\n", encoding="utf-8")
    profile = StartupProfile(
        container_names=(
            "nsddos-floodlight",
            "nsddos-sflowrt",
            "nsddos-labhost",
            "nsddos-detector",
        ),
        required_health_checks=("docker_daemon", "containers"),
        ui_host="127.0.0.1",
        ui_port=8010,
        health_timeout_seconds=90,
        health_poll_interval_seconds=2,
        session_path=session_path,
    )

    monkeypatch.setattr(
        "nsddos.bootstrap.reset_engine.confirm_install", lambda console, prompt: True
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.reset_engine.detect_compose_backend",
        lambda: ComposeBackend("docker-compose-v2", ("docker", "compose")),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.reset_engine.run_compose_command",
        lambda backend, args: subprocess.CompletedProcess(
            args, 0, stdout="[]", stderr=""
        ),
    )
    monkeypatch.setattr("nsddos.bootstrap.reset_engine.RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr("nsddos.bootstrap.reset_engine.LOG_DIR", logs_dir)
    monkeypatch.setattr("nsddos.bootstrap.reset_engine.CONFIG_PATH", config_path)
    monkeypatch.setattr(
        "nsddos.bootstrap.reset_engine.DEFAULT_STARTUP_PROFILE", profile
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.reset_engine.repair_runtime_state",
        lambda: ("runtime_dirs", "state"),
    )

    result = execute_reset(create_console(record=True))

    assert result.success is True
    assert not runtime_dir.exists()
    assert not logs_dir.exists()
    assert not session_path.exists()
    assert config_path.exists()
    assert result.preserved_config_path == str(config_path)


def test_execute_reset_cancelled_returns_unsuccessful_result(
    monkeypatch, tmp_path
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("name: nsddos\n", encoding="utf-8")
    monkeypatch.setattr(
        "nsddos.bootstrap.reset_engine.confirm_install", lambda console, prompt: False
    )
    monkeypatch.setattr("nsddos.bootstrap.reset_engine.CONFIG_PATH", config_path)

    result = execute_reset(create_console(record=True))

    assert result == ResetResult((), (), str(config_path), False)


def test_run_doctor_command_reruns_after_repairs(monkeypatch) -> None:
    first = (
        DiagnosticFinding(
            "docker", "docker_daemon", "fail", "Stopped", repairable=True, critical=True
        ),
    )
    second = (
        DiagnosticFinding(
            "docker",
            "docker_daemon",
            "pass",
            "Running",
            repairable=False,
            critical=False,
        ),
    )
    state = {"calls": 0}

    def fake_collect():
        state["calls"] += 1
        return first if state["calls"] == 1 else second

    monkeypatch.setattr(
        "nsddos.bootstrap.doctor.collect_diagnostic_findings", fake_collect
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.doctor.build_repair_plan",
        lambda findings: (
            type(
                "RepairAction",
                (),
                {
                    "area": "docker",
                    "title": "Repair Docker Prerequisites",
                    "detail": "repair",
                },
            )(),
        ),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.doctor.execute_repairs",
        lambda console, plan: ("Repair Docker Prerequisites",),
    )

    result = run_doctor_command(create_console(record=True))

    assert isinstance(result, DoctorResult)
    assert result.applied_repairs == ("Repair Docker Prerequisites",)
    assert result.unrepaired_failures == ()
    assert state["calls"] == 2


def test_cli_doctor_exits_nonzero_on_unrepaired_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        "nsddos.cli.run_doctor_command",
        lambda console: DoctorResult(
            findings=(),
            repair_plan=(),
            applied_repairs=(),
            unrepaired_failures=("docker:docker_daemon",),
        ),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1


def test_cli_reset_reports_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "nsddos.cli.run_reset_command",
        lambda console: ResetResult((), (), "/tmp/config.yaml", True),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["reset"])

    assert result.exit_code == 0

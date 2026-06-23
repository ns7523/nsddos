"""Tests for setup wizard."""

from __future__ import annotations

import subprocess

from typer.testing import CliRunner

from nsddos.bootstrap.planner import build_dependency_plan
from nsddos.bootstrap.profiles import DOCKER_RUNTIME_ONLY, FULL_SDN_LAB_MODE, get_profile_by_choice
from nsddos.bootstrap.questions import ask_deployment_profile
from nsddos.bootstrap.setup import collect_environment_scan
from nsddos.bootstrap.state import DependencyPlan, EnvironmentScan, SetupState, ToolStatus
from nsddos.bootstrap.terminal import create_console
from nsddos.bootstrap.wizard import render_setup_wizard
from nsddos.cli import app


def test_collect_environment_scan_detects_extended_fields(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.bootstrap.setup.platform.system", lambda: "Linux")
    monkeypatch.setattr("nsddos.bootstrap.setup.platform.python_version", lambda: "3.11.10")
    monkeypatch.setattr(
        "nsddos.bootstrap.environment.shutil.which",
        lambda name: f"/usr/bin/{name}" if name in {"docker", "git"} else None,
    )
    monkeypatch.setattr("nsddos.bootstrap.environment.sys.prefix", "/tmp/venv")
    monkeypatch.setattr("nsddos.bootstrap.environment.sys.base_prefix", "/usr")
    monkeypatch.setattr("nsddos.bootstrap.environment.os.sysconf", lambda name: 4096 if name == "SC_PAGE_SIZE" else 1024)
    monkeypatch.setattr(
        "nsddos.bootstrap.environment.shutil.disk_usage",
        lambda path: (100, 40, 60),
    )

    def fake_run(command, **kwargs):
        if command == ["docker", "info"]:
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")
        if command == ["docker", "compose", "version"]:
            return subprocess.CompletedProcess(command, 0, stdout="compose", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("nsddos.bootstrap.environment.subprocess.run", fake_run)

    scan = collect_environment_scan()

    assert isinstance(scan, EnvironmentScan)
    assert scan.os_family == "Linux"
    assert scan.python_version == "3.11.10"
    assert scan.virtualenv_active is True
    assert scan.docker.installed is True
    assert scan.docker_daemon_running is True
    assert scan.docker_compose.installed is True
    assert scan.docker_permissions_ready is False
    assert scan.git.installed is True
    assert scan.available_memory_bytes == 4096 * 1024
    assert scan.available_disk_bytes == 60
    assert isinstance(scan.missing_runtime_directories, tuple)


def test_get_profile_by_choice_returns_profile() -> None:
    profile = get_profile_by_choice(3)
    assert profile == DOCKER_RUNTIME_ONLY


def test_ask_deployment_profile_uses_prompt(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.bootstrap.questions.IntPrompt.ask", lambda *args, **kwargs: 4)
    profile = ask_deployment_profile(create_console(record=True))
    assert profile == FULL_SDN_LAB_MODE


def test_dependency_planning_orders_missing_requirements() -> None:
    scan = EnvironmentScan(
        os_name="Darwin",
        os_family="macOS",
        python_version="3.11.9",
        virtualenv_active=False,
        docker=ToolStatus(name="docker", installed=False, detail=None),
        docker_daemon_running=False,
        docker_compose=ToolStatus(name="docker-compose", installed=False, detail=None),
        docker_permissions_ready=False,
        git=ToolStatus(name="git", installed=True, detail="/usr/bin/git"),
        available_memory_bytes=4 * 1024**3,
        available_disk_bytes=10 * 1024**3,
        missing_runtime_directories=("/tmp/runtime",),
    )

    plan = build_dependency_plan(scan, FULL_SDN_LAB_MODE)

    assert isinstance(plan, DependencyPlan)
    titles = [item.title for item in plan.requirements]
    assert "Install Docker" in titles
    assert "Install Docker Compose" in titles
    assert "Create Virtual Environment" in titles
    assert "Configure Docker Permissions" in titles
    assert "Create Runtime Directories" in titles
    assert "Prepare Linux Host" in titles
    assert "Build Containers" in titles
    assert "Initialize Runtime" in titles


def test_render_setup_wizard_returns_setup_state(monkeypatch) -> None:
    scan = EnvironmentScan(
        os_name="Linux",
        os_family="Linux",
        python_version="3.11.9",
        virtualenv_active=True,
        docker=ToolStatus(name="docker", installed=True, detail="/usr/bin/docker"),
        docker_daemon_running=False,
        docker_compose=ToolStatus(name="docker-compose", installed=False, detail=None),
        docker_permissions_ready=False,
        git=ToolStatus(name="git", installed=True, detail="/usr/bin/git"),
        available_memory_bytes=16 * 1024**3,
        available_disk_bytes=40 * 1024**3,
        missing_runtime_directories=(),
    )
    monkeypatch.setattr("nsddos.bootstrap.wizard.collect_environment_scan", lambda: scan)
    monkeypatch.setattr("nsddos.bootstrap.wizard.ask_deployment_profile", lambda console: DOCKER_RUNTIME_ONLY)
    monkeypatch.setattr(
        "nsddos.bootstrap.wizard.execute_install_plan",
        lambda console, plan, scan: type(
            "InstallerResult",
            (),
            {
                "applied": (),
                "skipped_requirements": (),
                "failed_requirement": None,
                "rollback_results": (),
            },
        )(),
    )
    console = create_console(record=True)

    state = render_setup_wizard(console)
    output = console.export_text()

    assert isinstance(state, SetupState)
    assert state.scan == scan
    assert state.profile == DOCKER_RUNTIME_ONLY
    assert state.plan.profile == DOCKER_RUNTIME_ONLY
    assert "NSDDOS Setup Console" in output
    assert "Environment Scan" in output
    assert "Installation Plan" in output


def test_cli_setup_renders_wizard() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["setup"], input="2\nn\nn\nn\nn\nn\nn\n")

    assert result.exit_code == 0
    assert "NSDDOS Setup Console" in result.output
    assert "Environment Scan" in result.output
    assert "Installation Plan" in result.output

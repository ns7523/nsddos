"""Tests for premium terminal onboarding."""

from __future__ import annotations

import subprocess

from typer.testing import CliRunner

from nsddos.bootstrap import detect_environment
from nsddos.bootstrap.diagnostics import build_environment_diagnostics, readiness_label
from nsddos.bootstrap.environment import EnvironmentSnapshot, ToolStatus
from nsddos.bootstrap.terminal import create_console
from nsddos.bootstrap.welcome import build_welcome_renderable, render_welcome_screen
from nsddos.cli import app


def test_detect_environment_reports_typed_snapshot(monkeypatch) -> None:
    """Environment detection should return typed fields."""

    monkeypatch.setattr("nsddos.bootstrap.environment.platform.system", lambda: "Linux")
    monkeypatch.setattr("nsddos.bootstrap.environment.platform.python_version", lambda: "3.11.9")
    monkeypatch.setattr(
        "nsddos.bootstrap.environment.shutil.which",
        lambda name: f"/usr/bin/{name}" if name in {"docker", "git"} else None,
    )
    monkeypatch.setattr("nsddos.bootstrap.environment.sys.prefix", "/tmp/venv")
    monkeypatch.setattr("nsddos.bootstrap.environment.sys.base_prefix", "/usr")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="ok", stderr="")

    monkeypatch.setattr("nsddos.bootstrap.environment.subprocess.run", fake_run)

    snapshot = detect_environment()

    assert isinstance(snapshot, EnvironmentSnapshot)
    assert snapshot.os_family == "Linux"
    assert snapshot.python_version == "3.11.9"
    assert snapshot.docker.installed is True
    assert snapshot.docker_daemon_running is True
    assert snapshot.git.installed is True
    assert snapshot.virtualenv_active is True


def test_detect_environment_distinguishes_missing_docker(monkeypatch) -> None:
    """Docker install and daemon state should be separate."""

    monkeypatch.setattr("nsddos.bootstrap.environment.platform.system", lambda: "Darwin")
    monkeypatch.setattr("nsddos.bootstrap.environment.platform.python_version", lambda: "3.12.0")
    monkeypatch.setattr(
        "nsddos.bootstrap.environment.shutil.which",
        lambda name: "/usr/bin/git" if name == "git" else None,
    )
    monkeypatch.setattr("nsddos.bootstrap.environment.sys.prefix", "/usr")
    monkeypatch.setattr("nsddos.bootstrap.environment.sys.base_prefix", "/usr")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    def fail_run(*args, **kwargs):
        raise AssertionError("docker info should not run when docker missing")

    monkeypatch.setattr("nsddos.bootstrap.environment.subprocess.run", fail_run)

    snapshot = detect_environment()

    assert snapshot.os_family == "macOS"
    assert snapshot.docker.installed is False
    assert snapshot.docker_daemon_running is False
    assert snapshot.virtualenv_active is False


def test_welcome_render_contains_expected_sections() -> None:
    """Welcome screen should render core onboarding content."""

    snapshot = EnvironmentSnapshot(
        os_name="Linux",
        os_family="Linux",
        python_version="3.11.9",
        docker=ToolStatus(name="docker", installed=True, detail="/usr/bin/docker"),
        docker_daemon_running=True,
        git=ToolStatus(name="git", installed=True, detail="/usr/bin/git"),
        virtualenv_active=True,
    )
    console = create_console(record=True)

    console.print(build_welcome_renderable(snapshot))
    output = console.export_text()

    assert "NSDDOS" in output
    assert "Network Defense Runtime Engine" in output
    assert "Environment Scan" in output
    assert "Command Deck" in output
    assert "nsddos setup" in output
    assert "nsddos start" in output
    assert "nsddos doctor" in output


def test_render_welcome_screen_returns_snapshot(monkeypatch) -> None:
    """Render helper should return detected snapshot."""

    snapshot = EnvironmentSnapshot(
        os_name="Linux",
        os_family="Linux",
        python_version="3.11.9",
        docker=ToolStatus(name="docker", installed=False, detail=None),
        docker_daemon_running=False,
        git=ToolStatus(name="git", installed=True, detail="/usr/bin/git"),
        virtualenv_active=False,
    )
    monkeypatch.setattr("nsddos.bootstrap.welcome.detect_environment", lambda: snapshot)
    console = create_console(record=True)

    rendered = render_welcome_screen(console)
    output = console.export_text()

    assert rendered == snapshot
    assert "Readiness Matrix" in output
    assert "Degraded" in output


def test_diagnostics_are_deterministic_for_missing_tools() -> None:
    """Derived diagnostics should be deterministic."""

    snapshot = EnvironmentSnapshot(
        os_name="Linux",
        os_family="Linux",
        python_version="3.11.9",
        docker=ToolStatus(name="docker", installed=False, detail=None),
        docker_daemon_running=False,
        git=ToolStatus(name="git", installed=False, detail=None),
        virtualenv_active=False,
    )

    diagnostics = build_environment_diagnostics(snapshot)

    assert readiness_label(snapshot) == "Degraded"
    assert [item.status for item in diagnostics if item.label in {"Docker", "Git"}] == [
        "MISSING",
        "MISSING",
    ]


def test_cli_root_renders_welcome() -> None:
    """Bare CLI should render welcome screen."""

    runner = CliRunner()

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "NSDDOS" in result.output
    assert "Command Deck" in result.output


def test_cli_welcome_command_renders_welcome() -> None:
    """Explicit welcome command should render onboarding."""

    runner = CliRunner()

    result = runner.invoke(app, ["welcome"])

    assert result.exit_code == 0
    assert "Network Defense Runtime Engine" in result.output
    assert "Environment Scan" in result.output


def test_cli_version_still_works() -> None:
    """Existing commands should not be hijacked by welcome callback."""

    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "nsddos" in result.output.lower()

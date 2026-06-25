"""Tests for installer engine."""

from __future__ import annotations

import subprocess
from pathlib import Path

from nsddos.bootstrap.commands import venv_command
from nsddos.bootstrap.executors import CommandExecutionResult, run_system_command
from nsddos.bootstrap.installer import commands_for_requirement, execute_install_plan
from nsddos.bootstrap.os_profiles import OSProfile
from nsddos.bootstrap.package_manager import build_install_commands, select_package_manager
from nsddos.bootstrap.rollback import rollback_commands
from nsddos.bootstrap.state import DependencyPlan, DeploymentProfile, EnvironmentScan, InstallRequirement, ToolStatus
from nsddos.bootstrap.terminal import create_console


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
        "runtime_assets_ready": True,
        "runtime_assets_source": "repo",
        "runtime_assets_detail": "repository runtime payloads available",
    }
    payload.update(overrides)
    return EnvironmentScan(**payload)


def test_package_manager_selection_prefers_apt_for_ubuntu() -> None:
    manager = select_package_manager(
        OSProfile(family="Linux", distribution="ubuntu", package_manager="apt", supported=True, homebrew_installed=False)
    )
    commands = build_install_commands(manager, ("git",))
    assert manager.name == "apt"
    assert commands[0].argv == ("sudo", "apt", "update")
    assert commands[1].argv == ("sudo", "apt", "install", "-y", "git")


def test_commands_for_docker_install_are_generated() -> None:
    requirement = InstallRequirement("A", "Install Docker", "Docker required.")
    commands = commands_for_requirement(
        requirement,
        _scan(docker=ToolStatus(name="docker", installed=False, detail=None)),
        OSProfile(family="Linux", distribution="ubuntu", package_manager="apt", supported=True, homebrew_installed=False),
    )
    assert commands[0].argv == ("sudo", "apt", "update")
    assert commands[1].argv == ("sudo", "apt", "install", "-y", "docker.io")


def test_build_containers_requirement_uses_compose_command_kind() -> None:
    requirement = InstallRequirement("H", "Build Containers", "Build images.")

    commands = commands_for_requirement(
        requirement,
        _scan(),
        OSProfile(family="Linux", distribution="ubuntu", package_manager="apt", supported=True, homebrew_installed=False),
    )

    assert len(commands) == 1
    assert commands[0].kind == "compose"
    assert commands[0].compose_args == ("build",)


def test_download_runtime_assets_requirement_uses_asset_command() -> None:
    requirement = InstallRequirement("H", "Download Runtime Assets", "Download assets.")

    commands = commands_for_requirement(
        requirement,
        _scan(runtime_assets_ready=False),
        OSProfile(family="Linux", distribution="ubuntu", package_manager="apt", supported=True, homebrew_installed=False),
    )

    assert len(commands) == 1
    assert commands[0].kind == "asset-download"


def test_run_system_command_uses_v2_compose_backend(monkeypatch) -> None:
    command = commands_for_requirement(
        InstallRequirement("H", "Build Containers", "Build images."),
        _scan(),
        OSProfile(family="Linux", distribution="ubuntu", package_manager="apt", supported=True, homebrew_installed=False),
    )[0]
    captured: dict[str, tuple[str, ...]] = {}

    monkeypatch.setattr("nsddos.bootstrap.executors.resolve_compose_command", lambda: ("docker", "compose"))

    def fake_run(argv, **kwargs):
        captured["argv"] = tuple(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("nsddos.bootstrap.executors.subprocess.run", fake_run)

    result = run_system_command(command)

    assert result.success is True
    assert captured["argv"][:2] == ("docker", "compose")
    assert captured["argv"][-1] == "build"


def test_run_system_command_uses_v1_compose_backend(monkeypatch) -> None:
    command = commands_for_requirement(
        InstallRequirement("H", "Build Containers", "Build images."),
        _scan(),
        OSProfile(family="Linux", distribution="ubuntu", package_manager="apt", supported=True, homebrew_installed=False),
    )[0]
    captured: dict[str, tuple[str, ...]] = {}

    monkeypatch.setattr("nsddos.bootstrap.executors.resolve_compose_command", lambda: ("docker-compose",))

    def fake_run(argv, **kwargs):
        captured["argv"] = tuple(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("nsddos.bootstrap.executors.subprocess.run", fake_run)

    result = run_system_command(command)

    assert result.success is True
    assert captured["argv"][0] == "docker-compose"
    assert captured["argv"][-1] == "build"


def test_run_system_command_fails_cleanly_when_compose_backend_missing(monkeypatch) -> None:
    command = commands_for_requirement(
        InstallRequirement("H", "Build Containers", "Build images."),
        _scan(),
        OSProfile(family="Linux", distribution="ubuntu", package_manager="apt", supported=True, homebrew_installed=False),
    )[0]

    monkeypatch.setattr("nsddos.bootstrap.executors.resolve_compose_command", lambda: None)

    result = run_system_command(command)

    assert result.success is False
    assert result.stderr == "Compose backend unavailable"


def test_installer_execution_skips_on_non_approval(monkeypatch) -> None:
    plan = DependencyPlan(
        profile=DeploymentProfile("local-development", "Local Development", "dev"),
        requirements=(InstallRequirement("A", "Install Git", "Git required."),),
        summary="1 action",
    )
    console = create_console(record=True)
    monkeypatch.setattr("nsddos.bootstrap.installer.detect_os_profile", lambda: OSProfile("Linux", "ubuntu", "apt", True, False))
    monkeypatch.setattr("nsddos.bootstrap.installer.confirm_install", lambda console, prompt: False)

    result = execute_install_plan(console, plan, _scan(git=ToolStatus(name="git", installed=False, detail=None)))

    assert result.failed_requirement is None
    assert result.skipped_requirements == ("Install Git",)
    assert result.applied == ()


def test_installer_execution_runs_commands(monkeypatch) -> None:
    plan = DependencyPlan(
        profile=DeploymentProfile("local-development", "Local Development", "dev"),
        requirements=(InstallRequirement("E", "Create Virtual Environment", "Create venv"),),
        summary="1 action",
    )
    console = create_console(record=True)
    monkeypatch.setattr("nsddos.bootstrap.installer.detect_os_profile", lambda: OSProfile("Linux", "ubuntu", "apt", True, False))
    monkeypatch.setattr("nsddos.bootstrap.installer.confirm_install", lambda console, prompt: True)
    monkeypatch.setattr(
        "nsddos.bootstrap.installer.run_system_command",
        lambda command: CommandExecutionResult(command=command, success=True, returncode=0, stdout="ok", stderr=""),
    )

    result = execute_install_plan(console, plan, _scan(virtualenv_active=False))

    assert result.failed_requirement is None
    assert len(result.applied) == 1
    assert result.applied[0].command.kind == "venv"


def test_rollback_removes_created_venv(tmp_path) -> None:
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    command = venv_command("Create venv", "python3", str(venv_dir))

    results = rollback_commands((command,))

    assert len(results) == 1
    assert not Path(venv_dir).exists()

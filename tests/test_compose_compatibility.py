"""Tests for shared Compose compatibility resolution."""

from __future__ import annotations

import subprocess
from pathlib import Path

from nsddos.compose import compose_backend_name, resolve_compose_command
from nsddos.bootstrap.stack import list_stack_services
from nsddos.bootstrap.state import ComposeBackend
from nsddos.docker_manager import DockerManager


def test_resolve_compose_command_prefers_v2(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.compose.which", lambda name: "/usr/bin/docker" if name == "docker" else None)
    monkeypatch.setattr(
        "nsddos.compose.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout="v2", stderr=""),
    )

    assert resolve_compose_command() == ("docker", "compose")
    assert compose_backend_name(("docker", "compose")) == "docker-compose-v2"


def test_resolve_compose_command_falls_back_to_v1(monkeypatch) -> None:
    monkeypatch.setattr(
        "nsddos.compose.which",
        lambda name: "/usr/bin/docker-compose" if name == "docker-compose" else "/usr/bin/docker" if name == "docker" else None,
    )
    monkeypatch.setattr(
        "nsddos.compose.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="missing"),
    )

    assert resolve_compose_command() == ("docker-compose",)
    assert compose_backend_name(("docker-compose",)) == "docker-compose-v1"


def test_resolve_compose_command_returns_none_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.compose.which", lambda _name: None)

    assert resolve_compose_command() is None


def test_docker_manager_uses_shared_resolver(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.docker_manager.resolve_compose_command", lambda: ("docker-compose",))

    assert DockerManager._compose_backend() == ["docker-compose"]


def test_docker_manager_run_uses_resolved_compose_backend(monkeypatch, tmp_path) -> None:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services: {}\n", encoding="utf-8")
    manager = DockerManager(compose_file=compose_file)
    captured: dict[str, tuple[str, ...]] = {}

    monkeypatch.setattr("nsddos.docker_manager.resolve_compose_command", lambda: ("docker-compose",))

    def fake_run(argv, **kwargs):
        captured["argv"] = tuple(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")

    monkeypatch.setattr("nsddos.docker_manager.subprocess.run", fake_run)

    result = manager._run(["ps", "--format", "json"])

    assert result.returncode == 0
    assert captured["argv"] == ("docker-compose", "-f", str(compose_file), "ps", "--format", "json")


def test_docker_manager_get_service_states_falls_back_to_docker_ps(monkeypatch, tmp_path) -> None:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services: {}\n", encoding="utf-8")
    manager = DockerManager(compose_file=compose_file)

    monkeypatch.setattr("nsddos.docker_manager.resolve_compose_command", lambda: ("docker-compose",))
    monkeypatch.setattr("nsddos.docker_manager.DockerManager.is_docker_installed", staticmethod(lambda: True))
    monkeypatch.setattr("nsddos.docker_manager.DockerManager.is_daemon_running", lambda self: True)

    def fake_run(argv, **kwargs):
        if tuple(argv) == ("docker-compose", "-f", str(compose_file), "ps", "--format", "json"):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unknown flag: --format")
        if tuple(argv) == ("docker", "ps", "--format", "{{.Names}}|{{.Status}}"):
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=(
                    "nsddos-labhost|Up 10 minutes (healthy)\n"
                    "nsddos-floodlight|Up 10 minutes (healthy)\n"
                    "nsddos-sflowrt|Up 10 minutes (healthy)\n"
                    "nsddos-detector|Up 10 minutes (healthy)\n"
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {argv}")

    monkeypatch.setattr("nsddos.docker_manager.subprocess.run", fake_run)

    services = manager.get_service_states()

    assert [service.name for service in services] == [
        "nsddos-labhost",
        "nsddos-floodlight",
        "nsddos-sflowrt",
        "nsddos-detector",
    ]
    assert all(service.healthy for service in services)


def test_docker_manager_get_service_states_uses_compose_json_when_available(monkeypatch, tmp_path) -> None:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services: {}\n", encoding="utf-8")
    manager = DockerManager(compose_file=compose_file)

    monkeypatch.setattr("nsddos.docker_manager.resolve_compose_command", lambda: ("docker", "compose"))
    monkeypatch.setattr("nsddos.docker_manager.DockerManager.is_docker_installed", staticmethod(lambda: True))
    monkeypatch.setattr("nsddos.docker_manager.DockerManager.is_daemon_running", lambda self: True)

    def fake_run(argv, **kwargs):
        if tuple(argv) == ("docker", "compose", "-f", str(compose_file), "ps", "--format", "json"):
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout='{"Service":"labhost","State":"running","Health":"healthy","Name":"nsddos-labhost"}',
                stderr="",
            )
        raise AssertionError(f"unexpected command: {argv}")

    monkeypatch.setattr("nsddos.docker_manager.subprocess.run", fake_run)

    services = manager.get_service_states()

    assert len(services) == 1
    assert services[0].name == "labhost"
    assert services[0].healthy is True


def test_list_stack_services_uses_docker_manager_fallback(monkeypatch, tmp_path) -> None:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services: {}\n", encoding="utf-8")

    monkeypatch.setattr(
        "nsddos.bootstrap.stack.DockerManager.get_service_states",
        lambda self: [
            type(
                "Service",
                (),
                {
                    "name": "nsddos-labhost",
                    "status": "running",
                    "healthy": True,
                    "container_id": "abc123",
                    "detail": "Up 10 minutes (healthy)",
                },
            )(),
        ],
    )

    services = list_stack_services(
        ComposeBackend(name="docker-compose-v1", command=("docker-compose",)),
        compose_file=compose_file,
    )

    by_name = {service.container_name: service for service in services}
    assert len(services) == 4
    assert by_name["nsddos-labhost"].service_name == "nsddos-labhost"
    assert by_name["nsddos-labhost"].healthy is True
    assert by_name["nsddos-floodlight"].healthy is False
    assert by_name["nsddos-floodlight"].state == "missing"


def test_list_stack_services_prefixes_compose_service_name(monkeypatch, tmp_path) -> None:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services: {}\n", encoding="utf-8")

    monkeypatch.setattr(
        "nsddos.bootstrap.stack.DockerManager.get_service_states",
        lambda self: [
            type(
                "Service",
                (),
                {
                    "name": "labhost",
                    "status": "running",
                    "healthy": True,
                    "container_id": "abc123",
                    "detail": "healthy",
                },
            )(),
        ],
    )

    services = list_stack_services(
        ComposeBackend(name="docker-compose-v2", command=("docker", "compose")),
        compose_file=compose_file,
    )

    by_name = {service.container_name: service for service in services}
    assert len(services) == 4
    assert by_name["nsddos-labhost"].service_name == "nsddos-labhost"
    assert by_name["nsddos-labhost"].healthy is True
    assert by_name["nsddos-detector"].state == "missing"


def test_tracked_runtime_code_has_single_compose_probe_site() -> None:
    project_root = Path(__file__).resolve().parents[1]
    checked = (
        project_root / "src" / "nsddos" / "compose.py",
        project_root / "src" / "nsddos" / "bootstrap" / "stack.py",
        project_root / "src" / "nsddos" / "bootstrap" / "environment.py",
        project_root / "src" / "nsddos" / "docker_manager.py",
        project_root / "src" / "nsddos" / "bootstrap" / "installer.py",
        project_root / "src" / "nsddos" / "bootstrap" / "executors.py",
    )
    offenders: list[str] = []
    for path in checked:
        text = path.read_text(encoding="utf-8")
        if path.name != "compose.py" and "[\"docker\", \"compose\", \"version\"]" in text:
            offenders.append(str(path))
        if path.name != "compose.py" and "(\"docker\", \"compose\")" in text and "ComposeBackend" not in text:
            offenders.append(str(path))
    assert offenders == []

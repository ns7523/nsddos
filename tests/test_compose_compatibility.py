"""Tests for shared Compose compatibility resolution."""

from __future__ import annotations

import subprocess
from pathlib import Path

from nsddos.compose import compose_backend_name, resolve_compose_command
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

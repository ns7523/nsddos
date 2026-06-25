from __future__ import annotations

import subprocess

from nsddos.runtime.executor import RuntimeExecutor


def test_runtime_executor_executes_lab_via_docker_exec(monkeypatch) -> None:
    captured: dict[str, tuple[str, ...]] = {}

    def fake_run(args, **kwargs):
        captured["args"] = tuple(args)
        return subprocess.CompletedProcess(args, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr("nsddos.runtime.executor.subprocess.run", fake_run)

    result = RuntimeExecutor(lab_container="nsddos-labhost").execute_lab(["mn", "--version"], timeout=10)

    assert result.returncode == 0
    assert captured["args"] == ("docker", "exec", "nsddos-labhost", "mn", "--version")


def test_runtime_executor_parses_lab_link_index_map(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.runtime.executor.RuntimeExecutor.lab_container_running", lambda self: True)
    monkeypatch.setattr(
        "nsddos.runtime.executor.RuntimeExecutor.execute_lab",
        lambda self, args, detached=False, timeout=30: subprocess.CompletedProcess(
            args,
            0,
            stdout="1: lo: <LOOPBACK>\n2: s1-eth1@if3: <BROADCAST>\n3: s1-eth2@if4: <BROADCAST>\n",
            stderr="",
        ),
    )

    mapping = RuntimeExecutor().lab_link_index_map()

    assert mapping == {
        "1": "lo",
        "2": "s1-eth1",
        "3": "s1-eth2",
    }


def test_detect_runtime_capabilities_prefers_container_runtime(monkeypatch) -> None:
    from nsddos.runtime.capabilities import detect_runtime_capabilities

    monkeypatch.setattr("nsddos.runtime.capabilities.DockerManager.is_docker_installed", staticmethod(lambda: True))
    monkeypatch.setattr("nsddos.runtime.capabilities.DockerManager.is_daemon_running", lambda self: True)
    monkeypatch.setattr("nsddos.runtime.capabilities.RuntimeExecutor.lab_container_running", lambda self: True)

    caps = detect_runtime_capabilities()

    assert caps.docker_daemon is True
    assert caps.ovs_installed is True
    assert caps.ovs_service is True
    assert caps.mininet_supported is True
    assert caps.openflow_compatible is True
    assert caps.sflow_capable is True

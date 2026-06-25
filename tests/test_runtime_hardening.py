from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

from nsddos.runtime import cache as runtime_cache
from nsddos.runtime import convergence, identity, reconcile, topology
from nsddos.runtime.models import (
    ControllerTopology,
    InterfaceCorrelation,
    OpenFlowCorrelation,
    PathCorrelation,
    RuntimeState,
    SCHEMA_VERSION,
    TopologyCorrelation,
)
from nsddos.runtime.persistence import (
    PersistenceError,
    atomic_write_json,
    read_json_checked,
    recover_json,
)
from nsddos.runtime.providers_registry import build_provider_registry

PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"


def _atomic_write_worker(path_str: str, worker_id: int, iterations: int) -> None:
    from pathlib import Path

    from nsddos.runtime.persistence import atomic_write_json

    path = Path(path_str)
    for iteration in range(iterations):
        atomic_write_json(path, {"worker": worker_id, "iteration": iteration})


def _locked_update_worker(path_str: str, iterations: int) -> None:
    from pathlib import Path

    from nsddos.runtime.persistence import locked_update_json

    path = Path(path_str)
    for _ in range(iterations):
        locked_update_json(
            path,
            {"entries": []},
            lambda payload: {
                "entries": [*payload.get("entries", []), 1],
            },
        )


def _json_tree(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def _assert_json_tree_is_valid(root: Path) -> None:
    for path in _json_tree(root):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict), path
        assert payload.get("schema_version") == SCHEMA_VERSION, path
    assert list(root.rglob("*.tmp")) == []


def _run_cli_stress(
    home: Path, commands: list[list[str]]
) -> list[subprocess.CompletedProcess[str]]:
    env = os.environ.copy()
    env["NSDDOS_HOME"] = str(home)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_DIR) if not existing_pythonpath else f"{SRC_DIR}:{existing_pythonpath}"
    )
    processes = [
        subprocess.Popen(
            [sys.executable, "-m", "nsddos", *command],
            cwd=PROJECT_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for command in commands
    ]
    results: list[subprocess.CompletedProcess[str]] = []
    for process, command in zip(processes, commands):
        stdout, stderr = process.communicate(timeout=180)
        results.append(
            subprocess.CompletedProcess(
                args=[sys.executable, "-m", "nsddos", *command],
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        )
    return results


def test_persistence_detects_schema_and_recovers_corruption(tmp_path):
    path = tmp_path / "state.json"
    atomic_write_json(path, {"stack_running": False})

    payload = read_json_checked(path)
    assert payload["schema_version"] == SCHEMA_VERSION

    path.write_text('{"schema_version":"0.0"}', encoding="utf-8")
    with pytest.raises(PersistenceError):
        read_json_checked(path)

    path.write_text("{broken", encoding="utf-8")
    recovered = recover_json(path, RuntimeState().to_dict())
    assert recovered["schema_version"] == SCHEMA_VERSION
    assert recovered["stack_running"] is False


def test_atomic_write_json_is_safe_under_concurrent_writers(tmp_path):
    path = tmp_path / "state.json"
    errors: list[Exception] = []
    lock = threading.Lock()

    def worker(worker_id: int) -> None:
        for iteration in range(100):
            try:
                atomic_write_json(path, {"worker": worker_id, "iteration": iteration})
            except Exception as exc:  # pragma: no cover - failure path asserted below
                with lock:
                    errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert {"worker", "iteration"} <= set(payload)


def test_atomic_write_json_is_safe_under_100_parallel_processes(tmp_path):
    path = tmp_path / "state.json"
    ctx = multiprocessing.get_context("spawn")
    processes = [
        ctx.Process(target=_atomic_write_worker, args=(str(path), worker_id, 25))
        for worker_id in range(100)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=120)
        assert process.exitcode == 0

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert {"worker", "iteration"} <= set(payload)
    assert list(tmp_path.rglob("*.tmp")) == []


def test_locked_update_json_prevents_dropped_entries_under_100_parallel_processes(
    tmp_path,
):
    path = tmp_path / "history.json"
    ctx = multiprocessing.get_context("spawn")
    processes = [
        ctx.Process(target=_locked_update_worker, args=(str(path), 10))
        for _ in range(100)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=120)
        assert process.exitcode == 0

    payload = read_json_checked(path)
    assert len(payload["entries"]) == 1000


def test_runtime_cli_persistence_survives_100_parallel_processes(tmp_path):
    home = tmp_path / "nsddos-home"
    commands = (
        [["distributed-orchestrate"]] * 25
        + [["dashboard"]] * 25
        + [["release-build"]] * 25
        + [["runtime", "stream-start"]] * 25
    )
    results = _run_cli_stress(home, commands)

    assert all(result.returncode in {0, 1} for result in results)
    assert any((home / "runtime").rglob("*.json"))
    _assert_json_tree_is_valid(home / "runtime")


def test_runtime_cache_is_explicit_and_inspectable(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_cache, "CACHE_DIR", tmp_path)

    value, meta = runtime_cache.get_cache("collection", {"profile": "linux-native"})
    assert value is None
    assert meta["hit"] is False

    runtime_cache.set_cache("collection", {"profile": "linux-native"}, {"ok": True})
    value, meta = runtime_cache.get_cache("collection", {"profile": "linux-native"})

    assert value == {"ok": True}
    assert meta["hit"] is True
    assert runtime_cache.cache_summary()["entries"] == 1


def test_provider_registry_is_single_authoritative_construction_point():
    registry = build_provider_registry({"lab": {}, "api_port": 8008})
    assert sorted(registry) == ["floodlight", "mininet", "ovs", "sflowrt"]


def test_identity_normalization_detects_duplicate_controller_dpid(monkeypatch):
    class FakeMininet:
        def __init__(self, **kwargs):
            pass

        def topology_metadata(self):
            return SimpleNamespace(switches=["s1", "s2"])

    class FakeOVS:
        def __init__(self, **kwargs):
            pass

        def is_installed(self):
            return True

        def list_bridges(self):
            return ["s1", "s2"]

    class FakeFloodlight:
        def __init__(self, **kwargs):
            pass

        def switches(self):
            return [{"switchDPID": "00:01"}, {"switchDPID": "00:01"}]

    class FakeSFlow:
        def __init__(self, **kwargs):
            pass

        def is_reachable(self):
            return False

    monkeypatch.setattr(identity, "MininetProvider", FakeMininet)
    monkeypatch.setattr(identity, "OVSProvider", FakeOVS)
    monkeypatch.setattr(identity, "FloodlightProvider", FakeFloodlight)
    monkeypatch.setattr(identity, "SFlowProvider", FakeSFlow)
    monkeypatch.setattr(identity, "controller_history_summary", lambda config: {})

    result = identity.build_identity_map({"lab": {}, "api_port": 8008})

    assert [item.canonical_id for item in result.switches] == ["switch:s1", "switch:s2"]
    assert "duplicate_controller_dpid:00:01" in result.conflicts


def test_topology_correlation_reports_provider_mismatch(monkeypatch):
    class FakeMininet:
        def __init__(self, **kwargs):
            pass

        def topology_metadata(self):
            return SimpleNamespace(switches=["s1"], hosts=["h1", "h2", "h3"])

    fake_identity = SimpleNamespace(
        switches=[
            SimpleNamespace(
                canonical_id="switch:s1",
                mininet_name="s1",
                controller_dpid=None,
                ovs_bridge="s1",
            )
        ],
        conflicts=[],
    )
    fake_interfaces = SimpleNamespace(
        interfaces=[
            SimpleNamespace(
                ovs_name="s1-eth1", sflow_name=None, visible_in_sflow=False
            ),
        ],
        orphan_interfaces=[],
    )

    monkeypatch.setattr(topology, "MininetProvider", FakeMininet)
    monkeypatch.setattr(topology, "build_identity_map", lambda config: fake_identity)
    monkeypatch.setattr(
        topology, "correlate_interfaces", lambda config: fake_interfaces
    )

    result = topology.correlate_topology({"lab": {}})

    assert result.consistent is False
    assert result.missing_in_controller == ["s1"]
    assert result.missing_in_sflow == ["s1-eth1"]


def test_reconciliation_collects_missing_stale_and_orphan_entities(monkeypatch):
    monkeypatch.setattr(
        reconcile,
        "load_runtime_state",
        lambda: RuntimeState(stack_running=True, topology_state="stopped"),
    )
    monkeypatch.setattr(
        reconcile,
        "normalize_controller_topology",
        lambda config: ControllerTopology(stale_entities=["dpid:1"], links=[]),
    )
    monkeypatch.setattr(
        reconcile,
        "build_identity_map",
        lambda config: SimpleNamespace(conflicts=["duplicate_controller_dpid:1"]),
    )
    monkeypatch.setattr(
        reconcile,
        "correlate_interfaces",
        lambda config: InterfaceCorrelation(
            missing_interfaces=["iface:s1-eth1"], orphan_interfaces=["eth9"]
        ),
    )
    monkeypatch.setattr(
        reconcile,
        "correlate_openflow_ports",
        lambda config: OpenFlowCorrelation(
            missing_ports=["of:1"], stale_ports=["of:2"], orphan_ports=["of:3"]
        ),
    )
    monkeypatch.setattr(
        reconcile,
        "correlate_paths",
        lambda config: PathCorrelation(
            missing_paths=["path:s1-h1"], orphan_paths=["path:ghost"]
        ),
    )
    monkeypatch.setattr(
        reconcile,
        "correlate_topology",
        lambda config: TopologyCorrelation(
            missing_in_ovs=["s1"],
            missing_in_controller=["s1"],
            missing_in_sflow=["s1-eth1"],
            consistent=False,
        ),
    )

    result = reconcile.reconcile_runtime({})

    assert (
        "runtime_state:stack_running_without_topology" in result.inconsistent_entities
    )
    assert "switch:s1" in result.missing_entities
    assert "sflow:s1-eth1" in result.stale_entities
    assert "port:of:3" in result.orphan_entities


def test_convergence_distinguishes_partial_from_diverged(monkeypatch):
    monkeypatch.setattr(
        convergence,
        "normalize_controller_topology",
        lambda config: ControllerTopology(stale_entities=[]),
    )
    monkeypatch.setattr(
        convergence,
        "correlate_topology",
        lambda config: TopologyCorrelation(
            consistent=True, missing_in_sflow=["s1-eth1"]
        ),
    )
    monkeypatch.setattr(
        convergence, "correlate_openflow_ports", lambda config: OpenFlowCorrelation()
    )
    monkeypatch.setattr(
        convergence,
        "correlate_paths",
        lambda config: PathCorrelation(inconsistent_paths=["path:s1-h1"]),
    )

    result = convergence.validate_convergence({})

    assert result.status == "partially_converged"
    assert "telemetry_disagreement" in result.divergence_reasons

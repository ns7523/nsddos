"""Service runtime coordination tests."""

from __future__ import annotations

import importlib
from pathlib import Path


def _build_manager(tmp_path: Path, monkeypatch):
    import nsddos.service.persistence as persistence_module
    import nsddos.service.locks as locks_module
    import nsddos.service.manager as manager_module
    import nsddos.service.replay as replay_module

    importlib.reload(persistence_module)
    importlib.reload(locks_module)
    importlib.reload(replay_module)
    importlib.reload(manager_module)
    service_dir = tmp_path / "service"
    monkeypatch.setattr(persistence_module, "SERVICE_DIR", service_dir)
    monkeypatch.setattr(persistence_module, "SERVICE_STATE_PATH", service_dir / "state.json")
    monkeypatch.setattr(persistence_module, "SESSIONS_PATH", service_dir / "sessions.json")
    monkeypatch.setattr(persistence_module, "HEARTBEAT_PATH", service_dir / "heartbeat.json")
    monkeypatch.setattr(persistence_module, "EVENTS_PATH", service_dir / "events.jsonl")
    monkeypatch.setattr(persistence_module, "SYNC_PATH", service_dir / "synchronization.json")
    monkeypatch.setattr(locks_module, "LOCK_PATH", service_dir / "runtime.lock")
    return manager_module.RuntimeServiceManager({"lab": {"controller_port": 6653}}), persistence_module, replay_module


def test_service_session_lifecycle(tmp_path: Path, monkeypatch) -> None:
    manager, _, _ = _build_manager(tmp_path, monkeypatch)

    started = manager.start(owner="test")
    assert started.state == "running"
    assert started.active_session_id

    sessions = manager.sessions()
    assert sessions
    assert sessions[0]["state"] in {"active", "stopped"}

    stopped = manager.stop()
    assert stopped.state == "stopped"


def test_service_replay_and_stream_ordering(tmp_path: Path, monkeypatch) -> None:
    manager, _, replay_module = _build_manager(tmp_path, monkeypatch)

    manager.start(owner="test")
    manager.synchronize()
    manager.stop()

    replay = replay_module.replay_service_events()
    assert replay["event_count"] >= 3
    sequences = [event["sequence"] for event in replay["events"]]
    assert sequences == sorted(sequences)


def test_service_recovery_and_lock_consistency(tmp_path: Path, monkeypatch) -> None:
    manager, persistence_module, _ = _build_manager(tmp_path, monkeypatch)
    manager.start(owner="test")
    status = manager.status()
    assert status["lock_owner"] in {"test", "cli-service", "daemon"}
    diagnostics = manager.diagnostics()
    assert diagnostics["heartbeat_count"] >= 1
    assert persistence_module.SERVICE_STATE_PATH.exists() or persistence_module.SERVICE_DIR.exists()

"""Service persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import atomic_write_json, recover_json
from nsddos.service.models import RuntimeSession, ServiceState

SERVICE_DIR = RUNTIME_DIR / "service"
SERVICE_STATE_PATH = SERVICE_DIR / "state.json"
SESSIONS_PATH = SERVICE_DIR / "sessions.json"
HEARTBEAT_PATH = SERVICE_DIR / "heartbeat.json"
EVENTS_PATH = SERVICE_DIR / "events.jsonl"
SYNC_PATH = SERVICE_DIR / "synchronization.json"


def ensure_service_dirs() -> None:
    SERVICE_DIR.mkdir(parents=True, exist_ok=True)


def load_service_state() -> ServiceState:
    ensure_service_dirs()
    payload = recover_json(SERVICE_STATE_PATH, ServiceState().to_dict())
    return ServiceState.from_dict(payload)


def save_service_state(state: ServiceState) -> Path:
    ensure_service_dirs()
    return atomic_write_json(SERVICE_STATE_PATH, state.to_dict())


def load_sessions() -> list[RuntimeSession]:
    ensure_service_dirs()
    payload = recover_json(SESSIONS_PATH, {"sessions": []})
    return [RuntimeSession.from_dict(item) for item in payload.get("sessions", [])]


def save_sessions(sessions: list[RuntimeSession]) -> Path:
    ensure_service_dirs()
    return atomic_write_json(
        SESSIONS_PATH, {"sessions": [item.to_dict() for item in sessions]}
    )


def save_heartbeat(payload: dict[str, Any]) -> Path:
    ensure_service_dirs()
    return atomic_write_json(HEARTBEAT_PATH, payload)


def load_heartbeat() -> dict[str, Any]:
    ensure_service_dirs()
    return recover_json(HEARTBEAT_PATH, {"heartbeats": []})


def save_synchronization(payload: dict[str, Any]) -> Path:
    ensure_service_dirs()
    return atomic_write_json(SYNC_PATH, payload)


def load_synchronization() -> dict[str, Any]:
    ensure_service_dirs()
    return recover_json(SYNC_PATH, {"state": "unknown", "history": []})

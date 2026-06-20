"""Deterministic single-writer lock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from nsddos.service.persistence import SERVICE_DIR, ensure_service_dirs

LOCK_PATH = SERVICE_DIR / "runtime.lock"


@dataclass
class LockState:
    owner: str
    token: str
    acquired_at: str


def acquire_lock(owner: str, token: str) -> LockState:
    ensure_service_dirs()
    if LOCK_PATH.exists():
        existing = LOCK_PATH.read_text(encoding="utf-8").strip()
        if existing and existing != f"{owner}:{token}":
            raise RuntimeError(f"service lock already held by {existing.split(':', 1)[0]}")
    LOCK_PATH.write_text(f"{owner}:{token}", encoding="utf-8")
    return LockState(owner=owner, token=token, acquired_at=datetime.now(timezone.utc).isoformat())


def release_lock(owner: str, token: str) -> None:
    if not LOCK_PATH.exists():
        return
    current = LOCK_PATH.read_text(encoding="utf-8").strip()
    if current == f"{owner}:{token}":
        LOCK_PATH.unlink(missing_ok=True)


def current_lock_owner() -> str | None:
    if not LOCK_PATH.exists():
        return None
    content = LOCK_PATH.read_text(encoding="utf-8").strip()
    if not content:
        return None
    return content.split(":", 1)[0]

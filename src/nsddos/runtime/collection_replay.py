"""Replay persisted runtime collection snapshots."""

from __future__ import annotations

from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import read_json_checked

COLLECTION_DIR = RUNTIME_DIR / "collection"


def list_collection_snapshots() -> list[str]:
    """Return known collection snapshot paths."""
    if not COLLECTION_DIR.exists():
        return []
    return [str(path) for path in sorted(COLLECTION_DIR.glob("collection-*.json"))]


def replay_latest_collection() -> dict[str, Any]:
    """Load latest collection snapshot with schema validation."""
    snapshots = sorted(COLLECTION_DIR.glob("collection-*.json"))
    if not snapshots:
        return {"available": False, "detail": "no collection snapshots"}
    payload = read_json_checked(snapshots[-1])
    return {
        "available": True,
        "path": str(snapshots[-1]),
        "schema_version": payload.get("schema_version"),
        "provider_count": len(payload.get("provider_status", {})),
        "timings": payload.get("timings", {}),
        "cache": payload.get("cache", {}),
        "collection": payload,
    }

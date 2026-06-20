"""Deterministic inspectable runtime cache."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import atomic_write_json, read_json_checked

CACHE_DIR = RUNTIME_DIR / "cache"


def cache_key(name: str, inputs: dict[str, Any]) -> str:
    """Build deterministic cache key."""
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return f"{name}-{digest}"


def get_cache(name: str, inputs: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Read cache entry if present."""
    key = cache_key(name, inputs)
    path = CACHE_DIR / f"{key}.json"
    meta = {"key": key, "path": str(path), "hit": False}
    if not path.exists():
        return None, meta
    try:
        payload = read_json_checked(path)
    except Exception:
        return None, meta
    meta["hit"] = True
    return payload.get("value", {}), meta


def set_cache(name: str, inputs: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    """Write explicit cache entry."""
    key = cache_key(name, inputs)
    path = CACHE_DIR / f"{key}.json"
    payload = {
        "name": name,
        "key": key,
        "inputs": inputs,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "value": value,
    }
    atomic_write_json(path, payload)
    return {"key": key, "path": str(path), "hit": False}


def cache_summary() -> dict[str, Any]:
    """Return inspectable cache summary."""
    files = sorted(CACHE_DIR.glob("*.json")) if CACHE_DIR.exists() else []
    return {"entries": len(files), "files": [str(path) for path in files[-10:]]}

"""Collection snapshot persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.models import RuntimeCollectionBundle
from nsddos.runtime.persistence import atomic_write_json


def write_collection_snapshot(bundle: RuntimeCollectionBundle) -> Path:
    """Persist collection bundle."""
    snapshot_dir = RUNTIME_DIR / "collection"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = snapshot_dir / f"collection-{stamp}.json"
    atomic_write_json(path, bundle.to_dict())
    return path

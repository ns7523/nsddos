"""Runtime snapshot querying."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nsddos.constants import SNAPSHOT_DIR
from nsddos.runtime.query.models import RuntimeQuery
from nsddos.runtime.telemetry import compare_snapshots


def _snapshot_metadata(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    return {
        "id": path.stem,
        "path": str(path),
        "timestamp": payload.get("timestamp", ""),
        "schema_version": payload.get("schema_version", ""),
        "convergence": payload.get("convergence_state", {}).get("status", ""),
        "profile": payload.get("runtime_profile", {}).get("name", ""),
    }


def query_snapshots(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query snapshot metadata."""
    paths = sorted(SNAPSHOT_DIR.glob("snapshot-*.json")) if SNAPSHOT_DIR.exists() else []
    items = [_snapshot_metadata(path) for path in paths]
    lineage = [
        {
            "id": f"{a.stem}->{b.stem}",
            "record_type": "lineage",
            "source": a.stem,
            "target": b.stem,
        }
        for a, b in zip(paths, paths[1:])
    ]
    comparison = {}
    if len(paths) >= 2:
        comparison = compare_snapshots(paths[-2], paths[-1])
    filters = {item.field: item.value for item in query.filters}
    if filters.get("record_type") == "lineage":
        return {"items": lineage, "lineage": lineage}
    if filters.get("record_type") == "comparison":
        left = str(filters.get("left", ""))
        right = str(filters.get("right", ""))
        path_map = {path.stem: path for path in paths}
        if left in path_map and right in path_map:
            comparison = compare_snapshots(path_map[left], path_map[right])
        return {
            "items": [
                {
                    "id": f"{left}->{right}",
                    "record_type": "comparison",
                    "left": left,
                    "right": right,
                    "comparison": comparison,
                }
            ],
            "comparison": comparison,
        }
    return {"items": items, "lineage": lineage, "comparison": comparison}

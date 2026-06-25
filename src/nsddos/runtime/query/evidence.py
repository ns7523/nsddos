"""Runtime evidence querying."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import read_json_checked
from nsddos.runtime.query.models import RuntimeQuery

EVIDENCE_DIR = RUNTIME_DIR / "evidence"


def _evidence_item(path: Path) -> dict[str, Any]:
    payload = read_json_checked(path)
    return {
        "id": path.parent.name,
        "path": str(path),
        "timestamp": payload.get("snapshot", {}).get("timestamp", path.parent.name),
        "schema_version": payload.get("schema_version", ""),
        "convergence": payload.get("convergence", {}).get("status", ""),
        "verification_count": len(payload.get("verification", [])),
        "has_graph": bool(payload.get("graph")),
    }


def query_evidence(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query evidence bundles."""
    files = (
        sorted(EVIDENCE_DIR.glob("*/evidence.json")) if EVIDENCE_DIR.exists() else []
    )
    items = []
    for path in files:
        try:
            items.append(_evidence_item(path))
        except Exception:
            continue
    relationships = [
        {
            "source": item["id"],
            "target": item["convergence"],
            "type": "evidence_convergence",
        }
        for item in items
        if item.get("convergence")
    ]
    return {"items": items, "relationships": relationships}

"""Controller snapshot history."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nsddos.config import ensure_runtime_directories
from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.controller import normalize_controller_topology

CONTROLLER_HISTORY_PATH = RUNTIME_DIR / "controller-history.jsonl"


def record_controller_snapshot(config: dict[str, Any], path: Path = CONTROLLER_HISTORY_PATH) -> dict[str, Any]:
    """Persist normalized controller snapshot."""
    ensure_runtime_directories()
    topology = normalize_controller_topology(config)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topology": topology.to_dict(),
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload) + "\n")
    return payload


def load_controller_history(path: Path = CONTROLLER_HISTORY_PATH) -> list[dict[str, Any]]:
    """Load controller snapshot history."""
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def controller_history_summary(config: dict[str, Any]) -> dict[str, Any]:
    """Summarize controller changes over persisted snapshots."""
    history = load_controller_history()
    current = normalize_controller_topology(config).to_dict()
    previous = history[-1]["topology"] if history else {}
    previous_switches = {item.get("datapath_id") for item in previous.get("switches", []) if item.get("datapath_id")}
    current_switches = {item.get("datapath_id") for item in current.get("switches", []) if item.get("datapath_id")}
    return {
        "samples": len(history),
        "appeared_switches": sorted(current_switches - previous_switches),
        "disappeared_switches": sorted(previous_switches - current_switches),
        "topology_changed": previous != current if history else False,
    }

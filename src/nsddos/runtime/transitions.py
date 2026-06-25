"""Runtime transition analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nsddos.constants import SNAPSHOT_DIR
from nsddos.runtime.models import (
    ConvergenceTransition,
    DatapathTransition,
    DriftTransition,
    RuntimeTransition,
    TopologyTransition,
)


def _load_snapshot(path: Path) -> dict[str, Any]:
    """Load snapshot JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def list_snapshots(snapshot_dir: Path = SNAPSHOT_DIR) -> list[Path]:
    """List snapshot files sorted by name."""
    if not snapshot_dir.exists():
        return []
    return sorted(snapshot_dir.glob("snapshot-*.json"))


def _set(payload: Any, key: str) -> set[str]:
    """Extract set from dict list/string fields."""
    value = payload.get(key, []) if isinstance(payload, dict) else []
    if isinstance(value, list):
        return {str(item) for item in value}
    return set()


def analyze_snapshot_transitions(
    snapshot_a: dict[str, Any], snapshot_b: dict[str, Any]
) -> dict[str, Any]:
    """Analyze deterministic transition between 2 snapshots."""
    ts = str(snapshot_b.get("timestamp", ""))
    conv_a = snapshot_a.get("convergence_state", {}).get("status", "unknown")
    conv_b = snapshot_b.get("convergence_state", {}).get("status", "unknown")
    convergence = ConvergenceTransition(
        timestamp=ts,
        from_state=str(conv_a),
        to_state=str(conv_b),
        reasons=[
            str(item)
            for item in snapshot_b.get("convergence_state", {}).get(
                "divergence_reasons", []
            )
        ],
    )

    drift_a = _set(snapshot_a.get("reconciliation_state", {}), "stale_entities") | _set(
        snapshot_a.get("reconciliation_state", {}), "missing_entities"
    )
    drift_b = _set(snapshot_b.get("reconciliation_state", {}), "stale_entities") | _set(
        snapshot_b.get("reconciliation_state", {}), "missing_entities"
    )
    drift = DriftTransition(
        timestamp=ts,
        introduced=sorted(drift_b - drift_a),
        recovered=sorted(drift_a - drift_b),
        recurring=sorted(drift_a & drift_b),
    )

    topo_a = set(snapshot_a.get("topology_correlation", {}).get("graph_links", []))
    topo_b = set(snapshot_b.get("topology_correlation", {}).get("graph_links", []))
    topology = TopologyTransition(
        timestamp=ts,
        changed=topo_a != topo_b,
        added_links=sorted(topo_b - topo_a),
        removed_links=sorted(topo_a - topo_b),
        detail=f"links_a={len(topo_a)} links_b={len(topo_b)}",
    )

    ports_a = _set(snapshot_a.get("openflow_state", {}), "missing_ports") | {
        str(item.get("canonical_id"))
        for item in snapshot_a.get("openflow_state", {}).get("ports", [])
        if isinstance(item, dict)
    }
    ports_b = _set(snapshot_b.get("openflow_state", {}), "missing_ports") | {
        str(item.get("canonical_id"))
        for item in snapshot_b.get("openflow_state", {}).get("ports", [])
        if isinstance(item, dict)
    }
    dpid_a = {
        str(item.get("datapath_id"))
        for item in snapshot_a.get("controller_state", {}).get("switches", [])
        if isinstance(item, dict) and item.get("datapath_id")
    }
    dpid_b = {
        str(item.get("datapath_id"))
        for item in snapshot_b.get("controller_state", {}).get("switches", [])
        if isinstance(item, dict) and item.get("datapath_id")
    }
    datapath = DatapathTransition(
        timestamp=ts,
        added_ports=sorted(ports_b - ports_a),
        removed_ports=sorted(ports_a - ports_b),
        changed_dpids=sorted((dpid_a - dpid_b) | (dpid_b - dpid_a)),
        detail=f"ports_a={len(ports_a)} ports_b={len(ports_b)}",
    )

    runtime = RuntimeTransition(
        transition_type="runtime",
        from_state=str(conv_a),
        to_state=str(conv_b),
        affected_entities=sorted(
            set(
                drift.introduced
                + drift.recovered
                + topology.added_links
                + topology.removed_links
            )
        ),
        detail="snapshot_transition",
    )

    return {
        "runtime": runtime.to_dict(),
        "convergence": convergence.to_dict(),
        "drift": drift.to_dict(),
        "topology": topology.to_dict(),
        "datapath": datapath.to_dict(),
    }


def load_transition_history(snapshot_dir: Path = SNAPSHOT_DIR) -> list[dict[str, Any]]:
    """Build transition history from stored snapshots."""
    snapshots = list_snapshots(snapshot_dir)
    history: list[dict[str, Any]] = []
    for left, right in zip(snapshots, snapshots[1:]):
        history.append(
            analyze_snapshot_transitions(_load_snapshot(left), _load_snapshot(right))
        )
    return history

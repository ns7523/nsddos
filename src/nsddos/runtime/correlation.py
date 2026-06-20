"""Deterministic runtime event correlation."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.timeline import build_runtime_history_timeline
from nsddos.runtime.transitions import load_transition_history


def correlate_runtime_events() -> dict[str, Any]:
    """Correlate timeline + transitions into deterministic groups."""
    timeline = build_runtime_history_timeline()
    transitions = load_transition_history()

    groups = []
    recurring = []
    reasons: dict[str, int] = {}

    for item in transitions:
        conv = item.get("convergence", {})
        drift = item.get("drift", {})
        top = item.get("topology", {})
        datapath = item.get("datapath", {})
        affected_entities = (
            list(drift.get("introduced", []))
            + list(drift.get("recovered", []))
            + list(top.get("added_links", []))
            + list(top.get("removed_links", []))
            + list(datapath.get("added_ports", []))
            + list(datapath.get("removed_ports", []))
        )
        correlated = {
            "timestamp": conv.get("timestamp", ""),
            "cause": conv.get("to_state", "unknown"),
            "convergence_transition": f"{conv.get('from_state')}->{conv.get('to_state')}",
            "affected_entities": sorted(set(str(item) for item in affected_entities)),
            "introduced_drift": drift.get("introduced", []),
            "recovered_entities": drift.get("recovered", []),
            "topology_changed": bool(top.get("changed")),
            "causality_hints": list(conv.get("reasons", [])),
        }
        for reason in correlated["causality_hints"]:
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1
        groups.append(correlated)

    recurring = sorted([key for key, count in reasons.items() if count > 1])
    return {
        "groups": groups,
        "recurring_instability_patterns": recurring,
        "timeline_events": len(timeline),
        "transition_events": len(transitions),
    }

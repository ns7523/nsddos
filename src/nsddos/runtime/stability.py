"""Runtime stability analysis."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.correlation import correlate_runtime_events
from nsddos.runtime.replay import replay_execution_history
from nsddos.runtime.transitions import load_transition_history


def analyze_runtime_stability() -> dict[str, Any]:
    """Deterministically classify runtime stability."""
    transitions = load_transition_history()
    correlation = correlate_runtime_events()
    replay = replay_execution_history()

    recurring_failures = 0
    repeated_drift = 0
    unstable_entities: set[str] = set()
    for item in transitions:
        conv = item.get("convergence", {})
        drift = item.get("drift", {})
        if conv.get("to_state") in {"diverged", "partially_converged"}:
            recurring_failures += 1
        if drift.get("introduced") and drift.get("recurring"):
            repeated_drift += 1
            unstable_entities.update(drift.get("recurring", []))

    if recurring_failures == 0 and repeated_drift == 0:
        classification = "stable"
    elif recurring_failures > 2 or repeated_drift > 2:
        classification = "unstable"
    elif recurring_failures > 0 or repeated_drift > 0:
        classification = "degraded"
    else:
        classification = "transient"

    return {
        "classification": classification,
        "pipeline": (
            "unstable_pipeline"
            if replay.get("failed")
            else ("degraded_pipeline" if replay.get("warnings") else "stable_pipeline")
        ),
        "recurring_convergence_failures": recurring_failures,
        "repeated_drift_events": repeated_drift,
        "pipeline_warnings": len(replay.get("warnings", [])),
        "pipeline_failures": len(replay.get("failed", [])),
        "unstable_entities": sorted(unstable_entities),
        "recurring_instability_patterns": correlation.get(
            "recurring_instability_patterns", []
        ),
    }

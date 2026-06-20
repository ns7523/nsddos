"""Runtime analysis layer."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.confidence import runtime_confidence_summary
from nsddos.runtime.convergence import validate_convergence
from nsddos.runtime.correlation import correlate_runtime_events
from nsddos.runtime.dependencies import dependency_validation
from nsddos.runtime.drift import detect_runtime_drift
from nsddos.runtime.execution_graph import build_execution_graph
from nsddos.runtime.identity import build_identity_map
from nsddos.runtime.interfaces import correlate_interfaces
from nsddos.runtime.models import (
    FlowState,
    RuntimeAggregationResult,
    RuntimeAnalysisBundle,
    RuntimeCollectionBundle,
    TelemetryFreshness,
    VerificationResult,
)
from nsddos.runtime.openflow import correlate_openflow_ports
from nsddos.runtime.paths import correlate_paths
from nsddos.runtime.performance import timed
from nsddos.runtime.pipeline import build_execution_plan
from nsddos.runtime.reconcile import reconcile_runtime
from nsddos.runtime.replay import replay_execution_history
from nsddos.runtime.stability import analyze_runtime_stability
from nsddos.runtime.timeline import build_runtime_history_timeline, timeline_summary
from nsddos.runtime.topology import correlate_topology
from nsddos.runtime.transitions import load_transition_history


def analyze_runtime_bundle(config: dict[str, Any], collection: RuntimeCollectionBundle) -> RuntimeAnalysisBundle:
    """Analyze normalized collection bundle."""
    timings: dict[str, float] = {}
    topology = timed("topology_ms", timings, lambda: correlate_topology(config))
    identity = timed("identity_ms", timings, lambda: build_identity_map(config))
    interfaces = timed("interfaces_ms", timings, lambda: correlate_interfaces(config))
    openflow = timed("openflow_ms", timings, lambda: correlate_openflow_ports(config))
    paths = timed("paths_ms", timings, lambda: correlate_paths(config))
    reconciliation = timed("reconciliation_ms", timings, lambda: reconcile_runtime(config))
    convergence = timed("convergence_ms", timings, lambda: validate_convergence(config))
    drift = timed("drift_ms", timings, lambda: detect_runtime_drift(config))
    timeline_items = timed("timeline_ms", timings, build_runtime_history_timeline)
    transitions = timed("transitions_ms", timings, load_transition_history)
    correlation = timed("correlation_ms", timings, correlate_runtime_events)
    stability = timed("stability_ms", timings, analyze_runtime_stability)
    preset = "minimal-lab"
    execution = {
        "dependency": dependency_validation(),
        "plan": build_execution_plan(config, preset=preset).to_dict(),
        "graph": build_execution_graph(config, preset=preset),
        "replay": replay_execution_history(),
    }
    flows = FlowState(**collection.flow_state)
    freshness = TelemetryFreshness(**collection.freshness_state)
    seed = [
        VerificationResult("topology_consistency_seed", "pass" if topology.consistent else "warn", topology.detail, "runtime"),
        VerificationResult("flow_visibility_seed", "pass" if flows.telemetry_present else "warn", flows.detail, "runtime"),
        VerificationResult("telemetry_freshness_seed", "stale" if freshness.stale else "pass", freshness.detail, "runtime"),
    ]
    confidence = runtime_confidence_summary(topology, flows, freshness, seed, reconciliation)
    return RuntimeAnalysisBundle(
        topology=topology.to_dict(),
        identity=identity.to_dict(),
        interfaces=interfaces.to_dict(),
        openflow=openflow.to_dict(),
        paths=paths.to_dict(),
        reconciliation=reconciliation.to_dict(),
        convergence=convergence.to_dict(),
        drift=[item.to_dict() for item in drift],
        timeline={"timeline": [item.to_dict() for item in timeline_items], "summary": timeline_summary(timeline_items)},
        temporal={"transitions": transitions, "correlation": correlation, "stability": stability},
        execution=execution,
        confidence=confidence,
        timings=timings,
    )


def aggregate_runtime(config: dict[str, Any], collection: RuntimeCollectionBundle) -> RuntimeAggregationResult:
    """Return combined collection + analysis result."""
    analysis = analyze_runtime_bundle(config, collection)
    performance = {
        "collection": collection.timings,
        "analysis": analysis.timings,
        "cache": collection.cache,
    }
    return RuntimeAggregationResult(collection=collection, analysis=analysis, performance=performance)


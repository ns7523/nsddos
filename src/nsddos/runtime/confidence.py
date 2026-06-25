"""Deterministic runtime confidence summary."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.models import (
    FlowState,
    ReconciliationState,
    TelemetryFreshness,
    TopologyCorrelation,
    VerificationResult,
)


def runtime_confidence_summary(
    topology: TopologyCorrelation,
    flows: FlowState,
    freshness: TelemetryFreshness,
    verification: list[VerificationResult],
    reconciliation: ReconciliationState | None = None,
) -> dict[str, Any]:
    """Return deterministic operational confidence summary."""
    failed = sum(1 for item in verification if item.status == "fail")
    stale = sum(1 for item in verification if item.status == "stale")
    warnings = sum(1 for item in verification if item.status == "warn")

    topology_status = "healthy" if topology.consistent else "partial"
    telemetry_status = (
        "stale"
        if freshness.stale
        else ("visible" if flows.telemetry_present else "missing")
    )
    flow_status = "visible" if flows.flow_count > 0 else "empty"
    agreement = (
        "aligned" if failed == 0 and not topology.provider_agreement else "mismatch"
    )
    reductions = reconciliation.confidence_reductions if reconciliation else []
    datapath_status = "aligned"
    if any("datapath" in item or "port" in item for item in reductions):
        datapath_status = "partial"
    if any("telemetry_path" in item or "path" in item for item in reductions):
        datapath_status = "degraded"
    controller_status = "aligned"
    if any("controller" in item for item in reductions):
        controller_status = "partial"
    convergence_status = (
        "converged"
        if not reductions
        else ("partially_converged" if failed == 0 else "diverged")
    )
    stability_status = "stable"
    if any(
        "recurring" in item or "topology_disagreement" in item for item in reductions
    ):
        stability_status = "degraded"
    if any(
        "controller_topology_divergence" in item or "telemetry_path_divergence" in item
        for item in reductions
    ):
        stability_status = "unstable"
    reproducibility_status = (
        "reproducible"
        if failed == 0
        and controller_status == "aligned"
        and datapath_status == "aligned"
        else "partially_reproducible"
    )
    if failed > 0 and topology_status == "partial":
        reproducibility_status = "non_reproducible"

    return {
        "topology": topology_status,
        "telemetry": telemetry_status,
        "flows": flow_status,
        "datapath": datapath_status,
        "controller": controller_status,
        "convergence": convergence_status,
        "stability": stability_status,
        "reproducibility": reproducibility_status,
        "provider_agreement": agreement,
        "confidence_reductions": reductions,
        "failed_checks": failed,
        "warning_checks": warnings,
        "stale_checks": stale,
    }

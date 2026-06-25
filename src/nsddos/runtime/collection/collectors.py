"""Provider/runtime collectors only."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.capabilities import detect_runtime_capabilities
from nsddos.runtime.collection.registry import runtime_registry
from nsddos.runtime.controller import normalize_controller_topology
from nsddos.runtime.controller_state import controller_history_summary
from nsddos.runtime.environment import validate_runtime_environment
from nsddos.runtime.flows import sample_flow_visibility, telemetry_freshness
from nsddos.runtime.models import (
    FlowState,
    RuntimeCollectionBundle,
    TelemetryFreshness,
    TelemetryState,
)
from nsddos.runtime.performance import timed
from nsddos.runtime.profiles import detect_runtime_profile
from nsddos.runtime.providers.live.telemetry import (
    collect_live_telemetry,
    live_snapshot_to_collection_state,
)
from nsddos.runtime.simulation import (
    contract_to_collection_state,
    generate_attack_traffic,
)
from nsddos.runtime.providers_registry import collect_provider_status_from_registry
from nsddos.runtime.reproducibility import analyze_reproducibility


def build_telemetry_state_from_status(
    sflow_status: dict[str, Any],
    flows: FlowState,
    freshness: TelemetryFreshness,
) -> TelemetryState:
    """Build telemetry state from collected status."""
    return TelemetryState(
        collector_reachable=sflow_status.get("reachable", False),
        flow_api_ready=sflow_status.get("flows_accessible", False),
        metrics_available=sflow_status.get("metrics_accessible", False),
        topology_published=sflow_status.get("topology_accessible", False),
        active_flow_count=flows.flow_count,
        last_flow_timestamp=freshness.last_flow_timestamp,
        update_interval_seconds=freshness.sample_interval_seconds,
        stale=freshness.stale,
        visible_interfaces=flows.interfaces_visible,
    )


def collect_runtime_state(config: dict[str, Any]) -> RuntimeCollectionBundle:
    """Collect runtime/provider state only."""
    timings: dict[str, float] = {}
    live_enabled = bool(config.get("runtime", {}).get("live", {}).get("enabled", False))
    simulation_source_enabled = bool(
        config.get("runtime", {}).get("simulation", {}).get("source_enabled", False)
    )
    if live_enabled:
        live_snapshot = timed(
            "live_provider_collection_ms",
            timings,
            lambda: collect_live_telemetry(config),
        )
        live_state = timed(
            "live_collection_state_ms",
            timings,
            lambda: live_snapshot_to_collection_state(live_snapshot),
        )
        provider_status = dict(live_state["provider_status"])
        flows = FlowState(**live_state["flow_state"])
        freshness = TelemetryFreshness(**live_state["freshness_state"])
        telemetry = TelemetryState(**live_state["telemetry_state"])
    elif simulation_source_enabled:
        simulation_contract = timed(
            "simulation_collection_ms", timings, lambda: generate_attack_traffic(config)
        )
        simulation_state = timed(
            "simulation_collection_state_ms",
            timings,
            lambda: contract_to_collection_state(simulation_contract),
        )
        provider_status = dict(simulation_state["provider_status"])
        flows = FlowState(**simulation_state["flow_state"])
        freshness = TelemetryFreshness(**simulation_state["freshness_state"])
        telemetry = TelemetryState(**simulation_state["telemetry_state"])
    else:
        registry = timed(
            "provider_registry_ms", timings, lambda: runtime_registry(config)
        )
        provider_status = timed(
            "provider_status_ms",
            timings,
            lambda: collect_provider_status_from_registry(registry),
        )
        flows = timed(
            "flow_collection_ms",
            timings,
            lambda: sample_flow_visibility(config, interval=1.0),
        )
        freshness = timed(
            "freshness_collection_ms",
            timings,
            lambda: telemetry_freshness(config, interval=1.0),
        )
        telemetry = timed(
            "telemetry_normalization_ms",
            timings,
            lambda: build_telemetry_state_from_status(
                provider_status.get("sflowrt", {}), flows, freshness
            ),
        )
    controller = timed(
        "controller_collection_ms",
        timings,
        lambda: normalize_controller_topology(config),
    )
    profile = timed("profile_detection_ms", timings, detect_runtime_profile)
    capabilities = timed(
        "capability_detection_ms", timings, detect_runtime_capabilities
    )
    environment = timed(
        "environment_validation_ms",
        timings,
        lambda: validate_runtime_environment(config),
    )
    reproducibility = timed(
        "reproducibility_analysis_ms", timings, lambda: analyze_reproducibility(config)
    )
    return RuntimeCollectionBundle(
        provider_status=provider_status,
        flow_state=flows.to_dict(),
        freshness_state=freshness.to_dict(),
        telemetry_state=telemetry.to_dict(),
        controller_state=controller.to_dict(),
        controller_history=controller_history_summary(config),
        profile=profile.to_dict(),
        capabilities=capabilities.to_dict(),
        environment=environment.to_dict(),
        reproducibility=reproducibility.to_dict(),
        timings=timings,
        cache={"cache_hit": False, "policy": "explicit_no_silent_reuse"},
    )

"""Live mitigation enforcement wrapper."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from nsddos.providers.mininet.provider import HOST_IPS
from nsddos.runtime.mitigation.models import MitigationEvaluation
from nsddos.runtime.providers.live.registry import build_live_provider_registry


def _switch_dpid(provider: Any) -> str:
    switches = provider.switches() if hasattr(provider, "switches") else []
    if not switches:
        return "all"
    first = switches[0]
    return str(first.get("switchDPID") or first.get("dpid") or "all")


def _probe_plan(target_ip: str) -> tuple[str | None, str | None]:
    reverse = {ip: host for host, ip in HOST_IPS.items()}
    source_host = reverse.get(target_ip)
    if not source_host:
        return None, None
    for host, ip in HOST_IPS.items():
        if host != source_host:
            return source_host, ip
    return source_host, None


def _persist(evaluation: MitigationEvaluation) -> None:
    from nsddos.runtime.mitigation import engine as mitigation_engine

    mitigation_engine._persist_evaluation(evaluation)


def enforce_mitigation(
    config: dict[str, Any],
    evaluation: MitigationEvaluation,
    telemetry: dict[str, Any] | None = None,
) -> MitigationEvaluation:
    """Enforce previously evaluated mitigation decision."""
    if not evaluation.mitigation_required or evaluation.controller_payload is None:
        result = replace(
            evaluation,
            controller_mutation_status="not_attempted",
            ovs_insertion_status="not_attempted",
            flow_verification_status="not_attempted",
            traffic_block_status="not_attempted",
            enforcement_evidence={},
        )
        _persist(result)
        return result

    registry = build_live_provider_registry(config)
    bridge = str(config.get("lab", {}).get("ovs_bridge", "s1"))
    payload = dict(evaluation.controller_payload.floodlight_payload)
    payload["switch"] = _switch_dpid(registry.floodlight)

    controller_response = registry.floodlight.push_static_flow(payload)
    if not controller_response:
        result = replace(
            evaluation,
            mitigation_status="enforcement_failed",
            execution_result="controller_push_failed",
            controller_mutation_status="failed",
            enforcement_evidence={"controller_response": controller_response},
        )
        _persist(result)
        return result

    if not registry.ovs.install_drop_flow(
        bridge, evaluation.controller_payload.ovs_flow
    ):
        result = replace(
            evaluation,
            mitigation_status="enforcement_failed",
            execution_result="ovs_flow_insert_failed",
            controller_mutation_status="applied",
            ovs_insertion_status="failed",
            enforcement_evidence={
                "controller_response": controller_response,
                "bridge": bridge,
            },
        )
        _persist(result)
        return result

    controller_verified = registry.floodlight.static_flow_exists(
        evaluation.controller_payload.flow_rule.rule_id
    )
    ovs_verified = registry.ovs.has_flow(
        bridge, evaluation.controller_payload.verification_matches
    )
    if not controller_verified or not ovs_verified:
        result = replace(
            evaluation,
            mitigation_status="enforcement_failed",
            execution_result="flow_verification_failed",
            controller_mutation_status="applied",
            ovs_insertion_status="applied",
            flow_verification_status="failed",
            enforcement_evidence={
                "controller_response": controller_response,
                "controller_verified": controller_verified,
                "ovs_verified": ovs_verified,
                "bridge": bridge,
            },
        )
        _persist(result)
        return result

    source_host, destination_ip = _probe_plan(evaluation.target_ip)
    if not source_host or not destination_ip:
        result = replace(
            evaluation,
            mitigation_status="enforced",
            execution_result="traffic_probe_unavailable",
            controller_mutation_status="applied",
            ovs_insertion_status="applied",
            flow_verification_status="verified",
            traffic_block_status="unavailable",
            enforcement_evidence={
                "controller_response": controller_response,
                "controller_verified": controller_verified,
                "ovs_verified": ovs_verified,
            },
        )
        _persist(result)
        return result

    traffic_probe = registry.mininet.probe_traffic_drop(source_host, destination_ip)
    blocked = bool(traffic_probe.get("blocked"))
    result = replace(
        evaluation,
        mitigation_status="verified" if blocked else "enforcement_failed",
        execution_result=(
            "traffic_blocked_verified" if blocked else "traffic_verification_failed"
        ),
        controller_mutation_status="applied",
        ovs_insertion_status="applied",
        flow_verification_status="verified",
        traffic_block_status="blocked" if blocked else "failed",
        enforcement_evidence={
            "controller_response": controller_response,
            "controller_verified": controller_verified,
            "ovs_verified": ovs_verified,
            "traffic_probe": traffic_probe,
            "bridge": bridge,
        },
    )
    _persist(result)
    return result

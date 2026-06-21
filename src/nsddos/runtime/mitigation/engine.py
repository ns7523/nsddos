"""Deterministic mitigation engine."""

from __future__ import annotations

import ipaddress
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.providers.sflow.provider import SFlowProvider, resolve_sflowrt_api_url
from nsddos.runtime.collection_layer import collect_runtime_bundle
from nsddos.runtime.detection import evaluate_detection
from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.mitigation.actions import build_action
from nsddos.runtime.mitigation.controller import build_controller_payload
from nsddos.runtime.mitigation.evidence import build_mitigation_evidence
from nsddos.runtime.mitigation.models import MitigationEvaluation, MitigationPolicyDecision
from nsddos.runtime.mitigation.policies import evaluate_policy
from nsddos.runtime.mitigation.strategies import select_strategy
from nsddos.runtime.mitigation.validation import validate_mitigation_evaluation
from nsddos.runtime.policy import evaluate_dynamic_policy
from nsddos.runtime.policy.contracts_models import PolicyEvaluation
from nsddos.runtime.providers.live.telemetry import collect_live_telemetry, snapshot_to_detection_telemetry
from nsddos.runtime.simulation import contract_to_detection_telemetry, generate_attack_traffic
from nsddos.runtime.persistence import atomic_write_json, read_json_checked

MITIGATION_DIR = RUNTIME_DIR / "mitigation"


def _provider_url(config: dict[str, Any]) -> str:
    return resolve_sflowrt_api_url(config)


def _default_telemetry(config: dict[str, Any], reference_at: str | None = None) -> dict[str, Any]:
    if config.get("runtime", {}).get("live", {}).get("enabled", False):
        snapshot = collect_live_telemetry(config)
        return snapshot_to_detection_telemetry(snapshot)
    if config.get("runtime", {}).get("simulation", {}).get("source_enabled", False):
        contract = generate_attack_traffic(config)
        return contract_to_detection_telemetry(contract)
    bundle = collect_runtime_bundle(config)
    collector_reachable = bool(bundle.telemetry_state.get("collector_reachable", False))
    provider = SFlowProvider(api_url=_provider_url(config)) if collector_reachable else None
    flows = provider.flows() if provider is not None else []
    return {
        "provider_source": "sflowrt" if collector_reachable else "runtime-collection",
        "timestamp": reference_at or datetime.now(timezone.utc).isoformat(),
        "sample_window_seconds": bundle.freshness_state.get("sample_interval_seconds", 1.0) or 1.0,
        "flows": flows,
        "flow_state": bundle.flow_state,
        "telemetry_state": bundle.telemetry_state,
        "freshness_state": bundle.freshness_state,
        "replay_mode": False,
    }


def _flow_number(flow: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = flow.get(key)
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return 0.0


def _source_ip(flow: dict[str, Any]) -> str:
    for key in ("source", "src_ip", "src", "source_ip", "ipsource"):
        value = flow.get(key)
        if value:
            return str(value)
    return ""


def _severity_score(flow: dict[str, Any]) -> float:
    return (
        _flow_number(flow, "packets", "frames", "packet_count")
        + _flow_number(flow, "bytes", "octets", "byte_count") / 1000.0
        + _flow_number(flow, "connections", "flows", "connection_count") * 5.0
        + _flow_number(flow, "syn_rate", "udp_rate", "icmp_rate")
    )


def _select_target_ip(telemetry: dict[str, Any]) -> str:
    scores: dict[str, float] = defaultdict(float)
    for flow in telemetry.get("flows", []):
        if not isinstance(flow, dict):
            continue
        source = _source_ip(flow)
        if not source:
            continue
        try:
            ipaddress.ip_address(source)
        except ValueError:
            continue
        scores[source] += _severity_score(flow)
    if not scores:
        return ""
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return ranked[0][0]


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _persist_evaluation(evaluation: MitigationEvaluation) -> None:
    MITIGATION_DIR.mkdir(parents=True, exist_ok=True)
    payload = evaluation.to_dict()
    stamp = evaluation.timestamp.isoformat().replace(":", "").replace("-", "")
    atomic_write_json(MITIGATION_DIR / f"mitigation-{stamp}.json", payload)
    atomic_write_json(MITIGATION_DIR / "latest.json", payload)


def latest_mitigation_evidence() -> dict[str, Any]:
    path = MITIGATION_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def evaluate_mitigation(
    config: dict[str, Any],
    detection: DetectionEvaluation | None = None,
    policy: PolicyEvaluation | None = None,
    telemetry: dict[str, Any] | None = None,
    reference_at: str | None = None,
) -> MitigationEvaluation:
    payload = telemetry or _default_telemetry(config, reference_at=reference_at)
    detection_evaluation = detection or evaluate_detection(config, telemetry=payload, reference_at=reference_at)
    target_ip = _select_target_ip(payload)
    try:
        dynamic_policy = policy or evaluate_dynamic_policy(config, detection=detection_evaluation, telemetry=payload, reference_at=reference_at)
    except Exception:
        dynamic_policy = None
    policy_decision = (
        MitigationPolicyDecision(
            policy_name="policy_dynamic",
            mitigation_required=dynamic_policy.recommended_action != "alert_only",
            selected_action=dynamic_policy.recommended_action,
            reason=f"dynamic_policy escalation={dynamic_policy.escalation_level}",
        )
        if dynamic_policy is not None
        else evaluate_policy(detection_evaluation)
    )
    provider_reachable = bool(payload.get("telemetry_state", {}).get("collector_reachable", False))
    freshness_stale = bool(payload.get("freshness_state", {}).get("stale", False))
    replay_mode = bool(payload.get("replay_mode", False))
    strategy = select_strategy(
        detection_evaluation,
        policy_decision,
        provider_reachable=provider_reachable,
        replay_mode=replay_mode,
        freshness_stale=freshness_stale,
    )
    action = build_action(strategy.action_type, target_ip, policy_decision.reason)
    controller_payload = build_controller_payload(action)
    timestamp_text = str(payload.get("timestamp", detection_evaluation.telemetry_timestamp))
    evidence = build_mitigation_evidence(
        action=action,
        policy=policy_decision,
        strategy=strategy,
        controller_payload=controller_payload,
        confidence_score=detection_evaluation.confidence_score,
        attack_type=detection_evaluation.attack_type,
        risk_level=detection_evaluation.risk_level,
        detection_evidence_hash=detection_evaluation.evidence_hash,
        timestamp=timestamp_text,
    )
    evaluation = MitigationEvaluation(
        mitigation_required=strategy.action_type != "alert_only",
        mitigation_action=strategy.action_type,
        target_ip=action.target_ip,
        target_subnet=action.target_subnet,
        confidence_score=detection_evaluation.confidence_score,
        mitigation_status="planned" if strategy.action_type == "alert_only" else "dry_run_ready",
        execution_result="alert_only" if strategy.action_type == "alert_only" else "controller_payload_generated",
        mitigation_generation=evidence.mitigation_generation,
        mitigation_hash=evidence.mitigation_hash,
        timestamp=_parse_timestamp(timestamp_text),
        attack_type=detection_evaluation.attack_type,
        risk_level=detection_evaluation.risk_level,
        detection_evidence_hash=detection_evaluation.evidence_hash,
        policy=policy_decision,
        strategy=strategy,
        action_payload=action,
        controller_payload=controller_payload,
        created_at=timestamp_text,
    )
    errors = validate_mitigation_evaluation(evaluation)
    if errors:
        raise ValueError(f"mitigation evaluation invalid: {','.join(errors)}")
    _persist_evaluation(evaluation)
    return evaluation

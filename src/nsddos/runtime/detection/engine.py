"""Detection engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.providers.sflow.provider import SFlowProvider, resolve_sflowrt_api_url
from nsddos.runtime.collection_layer import collect_runtime_bundle
from nsddos.runtime.detection.anomaly import build_baseline, detect_anomalies
from nsddos.runtime.detection.classifier import classify_attack
from nsddos.runtime.detection.evidence import build_detection_evidence
from nsddos.runtime.detection.features import extract_feature_vector
from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.detection.risk import assess_risk
from nsddos.runtime.detection.scoring import anomaly_score, signature_score, traffic_intensity_score
from nsddos.runtime.detection.signatures import match_signatures
from nsddos.runtime.detection.validation import validate_detection_evaluation, validate_detection_telemetry
from nsddos.runtime.providers.live.telemetry import collect_live_telemetry, snapshot_to_detection_telemetry
from nsddos.runtime.simulation import contract_to_detection_telemetry, generate_attack_traffic
from nsddos.runtime.persistence import atomic_write_json, read_json_checked

DETECTION_DIR = RUNTIME_DIR / "detection"


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
    }


def _persist_evaluation(evaluation: DetectionEvaluation) -> None:
    DETECTION_DIR.mkdir(parents=True, exist_ok=True)
    payload = evaluation.to_dict()
    timestamp = evaluation.telemetry_timestamp.replace(":", "").replace("-", "")
    atomic_write_json(DETECTION_DIR / f"detection-{timestamp}.json", payload)
    atomic_write_json(DETECTION_DIR / "latest.json", payload)


def latest_detection_evidence() -> dict[str, Any]:
    path = DETECTION_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def evaluate_detection(
    config: dict[str, Any],
    telemetry: dict[str, Any] | None = None,
    reference_at: str | None = None,
) -> DetectionEvaluation:
    """Evaluate deterministic detection pipeline."""
    payload = telemetry or _default_telemetry(config, reference_at=reference_at)
    errors = validate_detection_telemetry(payload)
    if errors:
        raise ValueError(f"detection telemetry invalid: {','.join(errors)}")
    features = extract_feature_vector(payload)
    baseline, baseline_source = build_baseline()
    signatures = match_signatures(features)
    anomalies = detect_anomalies(features, baseline)
    signature_value = signature_score(signatures)
    anomaly_value = anomaly_score(anomalies)
    intensity_value = traffic_intensity_score(features)
    risk = assess_risk(signature_value, anomaly_value, intensity_value)
    classification = classify_attack(signatures, anomalies, risk)
    evidence = build_detection_evidence(payload, features, classification, risk)
    if classification.attack_detected:
        detection_status = "degraded" if baseline_source == "fallback" else "detected"
    else:
        detection_status = "normal"
    evaluation = DetectionEvaluation(
        attack_detected=classification.attack_detected,
        attack_type=classification.attack_type,
        confidence_score=risk.confidence_score,
        risk_level=risk.risk_level,
        evidence_hash=evidence.evidence_hash,
        classification_generation=evidence.classification_generation,
        detection_status=detection_status,
        telemetry_timestamp=str(payload.get("timestamp", datetime.now(timezone.utc).isoformat())),
        feature_vector=features,
        classification=classification,
        risk=risk,
        evidence=evidence,
        signatures=signatures,
        anomalies=anomalies,
        baseline_source=baseline_source,
    )
    validation_errors = validate_detection_evaluation(evaluation)
    if validation_errors:
        raise ValueError(f"detection evaluation invalid: {','.join(validation_errors)}")
    _persist_evaluation(evaluation)
    return evaluation

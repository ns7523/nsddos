"""Typed detection models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION


@dataclass(frozen=True)
class FeatureVector:
    packet_rate: float
    byte_rate: float
    connection_rate: float
    syn_rate: float
    ack_rate: float
    udp_rate: float
    icmp_rate: float
    entropy_score: float
    source_ip_cardinality: int
    destination_port_distribution: tuple[tuple[int, int], ...] = field(
        default_factory=tuple
    )
    connection_burst_factor: float = 0.0
    packet_size_variance: float = 0.0
    flow_duration: float = 0.0
    http_rate: float = 0.0
    partial_connection_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SignatureMatch:
    name: str
    matched: bool
    score: float
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnomalyResult:
    name: str
    triggered: bool
    current: float
    baseline: float
    threshold: float
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AttackClassification:
    attack_type: str
    severity: str
    attack_detected: bool
    confidence_score: float
    signature_score: float
    anomaly_score: float
    traffic_intensity_score: float
    matched_signatures: tuple[str, ...] = field(default_factory=tuple)
    triggered_anomalies: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskAssessment:
    risk_score: float
    risk_level: str
    confidence_score: float
    signature_score: float
    anomaly_score: float
    traffic_intensity_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DetectionEvidence:
    evidence_hash: str
    classification_generation: str
    provider_source: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DetectionEvaluation:
    attack_detected: bool
    attack_type: str
    confidence_score: float
    risk_level: str
    evidence_hash: str
    classification_generation: str
    detection_status: str
    telemetry_timestamp: str
    feature_vector: FeatureVector
    classification: AttackClassification
    risk: RiskAssessment
    evidence: DetectionEvidence
    signatures: tuple[SignatureMatch, ...] = field(default_factory=tuple)
    anomalies: tuple[AnomalyResult, ...] = field(default_factory=tuple)
    baseline_source: str = "fallback"
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "created_at": self.created_at,
            "attack_detected": self.attack_detected,
            "attack_type": self.attack_type,
            "confidence_score": self.confidence_score,
            "risk_level": self.risk_level,
            "evidence_hash": self.evidence_hash,
            "classification_generation": self.classification_generation,
            "detection_status": self.detection_status,
            "telemetry_timestamp": self.telemetry_timestamp,
            "feature_vector": self.feature_vector.to_dict(),
            "classification": self.classification.to_dict(),
            "risk": self.risk.to_dict(),
            "evidence": self.evidence.to_dict(),
            "signatures": [item.to_dict() for item in self.signatures],
            "anomalies": [item.to_dict() for item in self.anomalies],
            "baseline_source": self.baseline_source,
        }

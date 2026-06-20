"""Detection contracts and enums."""

from __future__ import annotations

DETECTION_ATTACK_TYPES = {
    "normal",
    "syn_flood",
    "udp_flood",
    "icmp_flood",
    "http_flood",
    "slowloris",
    "connection_exhaustion",
    "port_scanning",
    "volumetric_anomaly",
}

DETECTION_STATES = {"normal", "suspicious", "attack", "critical_attack"}
DETECTION_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
DETECTION_STATUS = {"normal", "detected", "degraded", "invalid"}

REQUIRED_TELEMETRY_FIELDS = (
    "provider_source",
    "timestamp",
    "flows",
    "flow_state",
    "telemetry_state",
    "freshness_state",
)

"""Deterministic detection thresholds and baselines."""

from __future__ import annotations

SIGNATURE_THRESHOLDS = {
    "syn_flood": {"min_syn_rate": 800.0, "ack_ratio_max": 0.35},
    "udp_flood": {"min_udp_rate": 1200.0},
    "icmp_flood": {"min_icmp_rate": 600.0, "min_icmp_share": 0.45},
    "http_flood": {"min_http_rate": 300.0, "min_connection_rate": 60.0},
    "slowloris": {"min_partial_connection_rate": 40.0, "min_flow_duration": 10.0},
    "connection_exhaustion": {"min_connection_rate": 400.0, "min_burst_factor": 25.0},
    "port_scanning": {"min_source_cardinality": 1, "min_port_span": 16, "max_entropy": 2.5},
    "volumetric_anomaly": {"min_packet_rate": 1500.0, "min_byte_rate": 1_000_000.0},
}

ANOMALY_THRESHOLDS = {
    "packet_anomaly": 3.0,
    "connection_anomaly": 3.0,
    "bandwidth_anomaly": 3.0,
    "latency_anomaly": 2.0,
    "flow_anomaly": 2.5,
}

DEFAULT_BASELINES = {
    "packet_rate": 250.0,
    "byte_rate": 150_000.0,
    "connection_rate": 80.0,
    "latency": 10.0,
    "flow_duration": 30.0,
}

SCORING_WEIGHTS = {
    "signature": 0.45,
    "anomaly": 0.35,
    "traffic_intensity": 0.20,
}

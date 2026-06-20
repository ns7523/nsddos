"""Deterministic signature matching."""

from __future__ import annotations

from nsddos.runtime.detection.models import FeatureVector, SignatureMatch
from nsddos.runtime.detection.thresholds import SIGNATURE_THRESHOLDS


def match_signatures(features: FeatureVector) -> tuple[SignatureMatch, ...]:
    """Evaluate signature rules against feature vector."""
    ack_ratio = features.ack_rate / max(features.syn_rate, 1.0)
    port_span = len(features.destination_port_distribution)
    signatures = (
        SignatureMatch(
            name="syn_flood",
            matched=features.syn_rate >= SIGNATURE_THRESHOLDS["syn_flood"]["min_syn_rate"]
            and ack_ratio <= SIGNATURE_THRESHOLDS["syn_flood"]["ack_ratio_max"],
            score=min(features.syn_rate / max(SIGNATURE_THRESHOLDS["syn_flood"]["min_syn_rate"], 1.0), 2.0),
            detail=f"syn_rate={features.syn_rate:.2f} ack_ratio={ack_ratio:.2f}",
        ),
        SignatureMatch(
            name="udp_flood",
            matched=features.udp_rate >= SIGNATURE_THRESHOLDS["udp_flood"]["min_udp_rate"],
            score=min(features.udp_rate / max(SIGNATURE_THRESHOLDS["udp_flood"]["min_udp_rate"], 1.0), 2.0),
            detail=f"udp_rate={features.udp_rate:.2f}",
        ),
        SignatureMatch(
            name="icmp_flood",
            matched=features.icmp_rate >= SIGNATURE_THRESHOLDS["icmp_flood"]["min_icmp_rate"]
            and (features.icmp_rate / max(features.packet_rate, 1.0)) >= SIGNATURE_THRESHOLDS["icmp_flood"]["min_icmp_share"],
            score=min(features.icmp_rate / max(SIGNATURE_THRESHOLDS["icmp_flood"]["min_icmp_rate"], 1.0), 2.0),
            detail=f"icmp_rate={features.icmp_rate:.2f}",
        ),
        SignatureMatch(
            name="http_flood",
            matched=features.http_rate >= SIGNATURE_THRESHOLDS["http_flood"]["min_http_rate"]
            and features.connection_rate >= SIGNATURE_THRESHOLDS["http_flood"]["min_connection_rate"],
            score=min(features.http_rate / max(SIGNATURE_THRESHOLDS["http_flood"]["min_http_rate"], 1.0), 2.0),
            detail=f"http_rate={features.http_rate:.2f} connections={features.connection_rate:.2f}",
        ),
        SignatureMatch(
            name="slowloris",
            matched=features.partial_connection_rate >= SIGNATURE_THRESHOLDS["slowloris"]["min_partial_connection_rate"]
            and features.flow_duration >= SIGNATURE_THRESHOLDS["slowloris"]["min_flow_duration"],
            score=min(features.partial_connection_rate / max(SIGNATURE_THRESHOLDS["slowloris"]["min_partial_connection_rate"], 1.0), 2.0),
            detail=f"partial_rate={features.partial_connection_rate:.2f} duration={features.flow_duration:.2f}",
        ),
        SignatureMatch(
            name="connection_exhaustion",
            matched=features.connection_rate >= SIGNATURE_THRESHOLDS["connection_exhaustion"]["min_connection_rate"]
            and features.connection_burst_factor >= SIGNATURE_THRESHOLDS["connection_exhaustion"]["min_burst_factor"],
            score=min(features.connection_burst_factor / max(SIGNATURE_THRESHOLDS["connection_exhaustion"]["min_burst_factor"], 1.0), 2.0),
            detail=f"connection_rate={features.connection_rate:.2f} burst={features.connection_burst_factor:.2f}",
        ),
        SignatureMatch(
            name="port_scanning",
            matched=features.source_ip_cardinality <= SIGNATURE_THRESHOLDS["port_scanning"]["min_source_cardinality"]
            and port_span >= SIGNATURE_THRESHOLDS["port_scanning"]["min_port_span"]
            and features.entropy_score <= SIGNATURE_THRESHOLDS["port_scanning"]["max_entropy"],
            score=min(port_span / max(SIGNATURE_THRESHOLDS["port_scanning"]["min_port_span"], 1.0), 2.0),
            detail=f"port_span={port_span} entropy={features.entropy_score:.2f}",
        ),
        SignatureMatch(
            name="volumetric_anomaly",
            matched=features.packet_rate >= SIGNATURE_THRESHOLDS["volumetric_anomaly"]["min_packet_rate"]
            and features.byte_rate >= SIGNATURE_THRESHOLDS["volumetric_anomaly"]["min_byte_rate"],
            score=min(features.byte_rate / max(SIGNATURE_THRESHOLDS["volumetric_anomaly"]["min_byte_rate"], 1.0), 2.0),
            detail=f"packet_rate={features.packet_rate:.2f} byte_rate={features.byte_rate:.2f}",
        ),
    )
    return signatures

"""ML baseline behavior tracking."""

from __future__ import annotations

from nsddos.runtime.ml.models import MLBaselineState, MLDatasetSnapshot


def build_baseline(dataset: MLDatasetSnapshot) -> MLBaselineState:
    rows = dataset.rows
    if not rows:
        return MLBaselineState(
            average_packet_rate=0.0,
            average_traffic_volume=0.0,
            average_connection_rate=0.0,
            average_entropy_score=0.0,
            protocol_baseline=(("tcp", 0.0), ("udp", 0.0), ("icmp", 0.0)),
            flow_baseline=0.0,
        )
    packet_rate = sum(item.feature_vector.packet_rate for item in rows) / len(rows)
    byte_rate = sum(item.feature_vector.byte_rate for item in rows) / len(rows)
    connection_rate = sum(item.feature_vector.connection_rate for item in rows) / len(rows)
    entropy_score = sum(item.feature_vector.entropy_score for item in rows) / len(rows)
    syn = sum(item.feature_vector.syn_rate for item in rows)
    udp = sum(item.feature_vector.udp_rate for item in rows)
    icmp = sum(item.feature_vector.icmp_rate for item in rows)
    total = max(syn + udp + icmp, 1.0)
    return MLBaselineState(
        average_packet_rate=packet_rate,
        average_traffic_volume=byte_rate,
        average_connection_rate=connection_rate,
        average_entropy_score=entropy_score,
        protocol_baseline=(
            ("tcp", syn / total),
            ("udp", udp / total),
            ("icmp", icmp / total),
        ),
        flow_baseline=sum(item.feature_vector.flow_duration for item in rows) / len(rows),
    )

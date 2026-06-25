"""Structured dashboard chart payloads."""

from __future__ import annotations

from nsddos.dashboard.contracts import (
    AttackState,
    MLMetricsState,
    PolicyAnalytics,
    StreamState,
    VisualizationSeries,
)


def build_visualizations(
    streams: StreamState,
    attacks: AttackState,
    policy_analytics: PolicyAnalytics,
    ml_metrics: MLMetricsState,
    cluster_nodes: int,
    cluster_health: str,
) -> tuple[VisualizationSeries, ...]:
    """Build deterministic chart payloads."""
    health_score = (
        1.0
        if cluster_health == "healthy"
        else (0.5 if cluster_health == "degraded" else 0.0)
    )
    return (
        VisualizationSeries(
            "throughput",
            "Throughput",
            (
                ("event_throughput", streams.event_throughput),
                ("queue_depth", float(streams.queue_depth)),
            ),
        ),
        VisualizationSeries(
            "attack_distribution",
            "Attack Distribution",
            tuple((name, float(count)) for name, count in attacks.attack_types),
        ),
        VisualizationSeries(
            "mitigation_history",
            "Mitigation History",
            (
                ("policy_events", float(policy_analytics.policy_events)),
                ("escalations", float(policy_analytics.escalation_frequency)),
            ),
        ),
        VisualizationSeries(
            "cluster_health",
            "Cluster Health",
            (("cluster_nodes", float(cluster_nodes)), ("health_score", health_score)),
        ),
        VisualizationSeries(
            "ml_confidence",
            "ML Confidence",
            (
                ("confidence", ml_metrics.ml_confidence),
                ("drift", ml_metrics.drift_trend[0] if ml_metrics.drift_trend else 0.0),
            ),
        ),
    )

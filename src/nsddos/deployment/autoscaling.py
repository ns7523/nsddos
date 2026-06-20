"""Deterministic autoscaling policy."""

from __future__ import annotations

from nsddos.deployment.contracts import AutoscalingPolicy


def build_autoscaling_policy(container_count: int) -> AutoscalingPolicy:
    """Build deterministic autoscaling thresholds."""
    max_replicas = max(3, container_count * 2)
    return AutoscalingPolicy(
        min_replicas=1,
        max_replicas=max_replicas,
        cpu_percent_threshold=70,
        memory_percent_threshold=75,
        request_rate_threshold=500,
        scale_up_step=1,
        scale_down_step=1,
    )

"""Deterministic rate-limit payload builders."""

from __future__ import annotations

from nsddos.runtime.mitigation.models import MitigationActionPayload


def build_rate_limit_action(target_ip: str, reason: str) -> MitigationActionPayload:
    return MitigationActionPayload(
        action_type="rate_limit",
        target_ip=target_ip,
        duration_seconds=1200,
        bandwidth_mbps=100,
        packet_rate_limit=1200,
        connection_limit=250,
        reason=reason,
    )

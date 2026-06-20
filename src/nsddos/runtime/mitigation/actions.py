"""Mitigation action builders."""

from __future__ import annotations

from nsddos.runtime.mitigation.blocking import build_block_action
from nsddos.runtime.mitigation.models import MitigationActionPayload
from nsddos.runtime.mitigation.quarantine import build_quarantine_action
from nsddos.runtime.mitigation.ratelimit import build_rate_limit_action


def build_action(action_type: str, target_ip: str, reason: str) -> MitigationActionPayload:
    if action_type in {"block_ip", "temporary_ban", "drop_traffic", "permanent_ban"}:
        return build_block_action(action_type, target_ip, reason)
    if action_type == "rate_limit":
        return build_rate_limit_action(target_ip, reason)
    if action_type in {"quarantine_host", "isolate_subnet"}:
        return build_quarantine_action(action_type, target_ip, reason)
    if action_type == "connection_reset":
        return MitigationActionPayload(
            action_type="connection_reset",
            target_ip=target_ip,
            duration_seconds=300,
            reset_connections=True,
            reason=reason,
        )
    return MitigationActionPayload(action_type="alert_only", reason=reason)

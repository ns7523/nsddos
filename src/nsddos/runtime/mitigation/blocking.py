"""Deterministic blocking payload builders."""

from __future__ import annotations

import hashlib

from nsddos.runtime.domain.serialization import to_canonical_json
from nsddos.runtime.mitigation.models import MitigationActionPayload


def build_block_action(
    action_type: str, target_ip: str, reason: str
) -> MitigationActionPayload:
    duration = (
        86400
        if action_type == "permanent_ban"
        else 900 if action_type == "temporary_ban" else 3600
    )
    payload = MitigationActionPayload(
        action_type=action_type,
        target_ip=target_ip,
        duration_seconds=duration,
        reason=reason,
    )
    return payload


def block_evidence(action: MitigationActionPayload) -> str:
    return hashlib.sha256(
        to_canonical_json(action.to_dict()).encode("utf-8")
    ).hexdigest()

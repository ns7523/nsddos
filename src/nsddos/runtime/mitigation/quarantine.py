"""Deterministic quarantine payload builders."""

from __future__ import annotations

import ipaddress

from nsddos.runtime.mitigation.models import MitigationActionPayload


def derive_subnet(target_ip: str) -> str:
    network = ipaddress.ip_network(f"{target_ip}/24", strict=False)
    return str(network)


def build_quarantine_action(
    action_type: str, target_ip: str, reason: str
) -> MitigationActionPayload:
    subnet = derive_subnet(target_ip) if action_type == "isolate_subnet" else ""
    return MitigationActionPayload(
        action_type=action_type,
        target_ip=target_ip,
        target_subnet=subnet,
        duration_seconds=1800,
        connection_limit=0,
        reason=reason,
    )

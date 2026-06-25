"""Controller payload generation."""

from __future__ import annotations

import hashlib
from typing import Any

from nsddos.runtime.domain.serialization import to_canonical_json
from nsddos.runtime.mitigation.models import (
    MitigationActionPayload,
    MitigationControllerPayload,
    MitigationFlowRule,
)


def build_controller_payload(
    action: MitigationActionPayload,
) -> MitigationControllerPayload | None:
    if action.action_type == "alert_only":
        return None
    match_field = "nw_src"
    match_value = action.target_subnet or action.target_ip
    flow_rule = MitigationFlowRule(
        rule_id=hashlib.sha256(
            f"{action.action_type}:{match_value}:{action.duration_seconds}".encode(
                "utf-8"
            )
        ).hexdigest()[:16],
        priority=50000,
        match_field=match_field,
        match_value=match_value,
        action_type=action.action_type,
        duration_seconds=action.duration_seconds,
    )
    floodlight_payload: dict[str, Any] = {
        "switch": "detected-at-enforce",
        "name": flow_rule.rule_id,
        "active": "true",
        "priority": str(flow_rule.priority),
        "eth_type": "0x0800",
        "src-ip": action.target_ip,
        "actions": "drop",
    }
    ovs_flow = (
        f"priority={flow_rule.priority},ip,{match_field}={match_value},actions=drop"
    )
    verification_matches = {match_field: match_value, "actions": "drop"}
    payload_seed = {
        "action": action.to_dict(),
        "flow_rule": flow_rule.to_dict(),
        "floodlight_payload": floodlight_payload,
        "ovs_flow": ovs_flow,
    }
    payload_hash = hashlib.sha256(
        to_canonical_json(payload_seed).encode("utf-8")
    ).hexdigest()
    return MitigationControllerPayload(
        controller_type="floodlight-ovs-lab",
        provider_target="floodlight-staticflow-plus-ovs",
        flow_rule=flow_rule,
        payload_hash=payload_hash,
        command=f"enforce:{action.action_type}:{match_value}",
        floodlight_payload=floodlight_payload,
        ovs_flow=ovs_flow,
        verification_matches=verification_matches,
    )

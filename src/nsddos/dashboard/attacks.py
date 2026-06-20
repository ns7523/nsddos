"""Dashboard attack aggregation."""

from __future__ import annotations

from collections import Counter

from nsddos.dashboard.contracts import AttackState, DashboardSourceBundle


def build_attack_state(sources: DashboardSourceBundle) -> AttackState:
    """Aggregate attack state."""
    detection = sources.detection
    mitigation = sources.mitigation
    policy_history = sources.policy_history
    active_attacks = 1 if detection.get("attack_detected", False) else 0
    attack_types = Counter()
    severities = Counter()
    source_ips = Counter()
    history_counts: list[int] = []
    if detection.get("attack_type"):
        attack_types[str(detection.get("attack_type", "normal"))] += 1
        severities[str(detection.get("risk_level", "LOW"))] += 1
    if mitigation.get("target_ip"):
        source_ips[str(mitigation.get("target_ip", ""))] += 1
    for item in policy_history:
        attack_type = str(item.get("attack_type", "normal"))
        if attack_type not in {"", "normal"}:
            attack_types[attack_type] += 1
            history_counts.append(1)
        source_ip = str(item.get("source_ip", ""))
        if source_ip:
            source_ips[source_ip] += 1
    return AttackState(
        active_attacks=active_attacks,
        attack_types=tuple(sorted(attack_types.items())),
        source_ips=tuple(sorted(source_ips.items())),
        attack_severities=tuple(sorted(severities.items())),
        attack_frequency_history=tuple(history_counts or [active_attacks]),
    )

"""Dashboard threat intelligence aggregation."""

from __future__ import annotations

from collections import Counter

from nsddos.dashboard.contracts import DashboardSourceBundle, ThreatIntelState


def build_threat_intel_state(sources: DashboardSourceBundle) -> ThreatIntelState:
    """Aggregate repeated attackers and subnet patterns."""
    repeated = Counter()
    subnets = set()
    protocols = Counter()
    for item in sources.policy_history:
        source_ip = str(item.get("source_ip", ""))
        if source_ip:
            repeated[source_ip] += 1
            parts = source_ip.split(".")
            if len(parts) == 4:
                subnets.add(".".join(parts[:3]) + ".0/24")
        attack_type = str(item.get("attack_type", ""))
        if attack_type:
            protocols[attack_type] += 1
    total = sum(protocols.values()) or 1
    concentration = tuple(
        sorted((name, count / total) for name, count in protocols.items())
    )
    recurrence_frequency = sum(count for _, count in repeated.items() if count > 1)
    return ThreatIntelState(
        repeated_attacker_ips=tuple(
            sorted((ip, count) for ip, count in repeated.items() if count > 0)
        ),
        recurrence_frequency=recurrence_frequency,
        high_risk_subnets=tuple(sorted(subnets)),
        suspicious_protocol_concentration=concentration,
    )

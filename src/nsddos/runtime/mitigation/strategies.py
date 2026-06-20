"""Mitigation strategy selection."""

from __future__ import annotations

from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.mitigation.models import MitigationPolicyDecision, MitigationStrategySelection


def select_strategy(
    detection: DetectionEvaluation,
    policy: MitigationPolicyDecision,
    *,
    provider_reachable: bool,
    replay_mode: bool,
    freshness_stale: bool,
) -> MitigationStrategySelection:
    if replay_mode:
        return MitigationStrategySelection("strategy_alert_only", "alert_only", "replay_safe", "replay mode suppresses live-style mitigation")
    if freshness_stale or not provider_reachable:
        return MitigationStrategySelection("strategy_alert_only", "alert_only", "degraded_input", "provider or freshness state degraded")
    mapping = {
        "block_ip": "strategy_block_ip",
        "drop_traffic": "strategy_drop_traffic",
        "rate_limit": "strategy_rate_limit",
        "quarantine_host": "strategy_quarantine_host",
        "isolate_subnet": "strategy_isolate_subnet",
        "temporary_ban": "strategy_temporary_ban",
        "connection_reset": "strategy_connection_reset",
        "permanent_ban": "strategy_permanent_ban",
        "alert_only": "strategy_alert_only",
    }
    detail = f"attack_type={detection.attack_type} risk_level={detection.risk_level} confidence={detection.confidence_score:.4f}"
    return MitigationStrategySelection(
        mapping[policy.selected_action],
        policy.selected_action,
        "dry_run",
        detail,
    )

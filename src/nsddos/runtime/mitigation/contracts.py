"""Mitigation contract constants."""

from __future__ import annotations

MITIGATION_ACTIONS = {
    "block_ip",
    "drop_traffic",
    "rate_limit",
    "quarantine_host",
    "isolate_subnet",
    "temporary_ban",
    "connection_reset",
    "permanent_ban",
    "alert_only",
}

MITIGATION_STATUSES = {
    "planned",
    "dry_run_ready",
    "enforced",
    "verified",
    "enforcement_failed",
    "validation_failed",
}

EXECUTION_RESULTS = {
    "controller_payload_generated",
    "alert_only",
    "controller_rule_enforced",
    "flow_rule_verified",
    "traffic_blocked_verified",
    "controller_push_failed",
    "ovs_flow_insert_failed",
    "flow_verification_failed",
    "traffic_verification_failed",
    "traffic_probe_unavailable",
    "validation_failed",
}

ENFORCEMENT_STEP_STATUSES = {
    "not_attempted",
    "applied",
    "failed",
    "verified",
    "blocked",
    "unavailable",
}

REQUIRES_TARGET_IP = {
    "block_ip",
    "drop_traffic",
    "rate_limit",
    "quarantine_host",
    "temporary_ban",
    "connection_reset",
    "permanent_ban",
}

REQUIRES_SUBNET = {"isolate_subnet"}

POLICY_NAMES = {
    "policy_alert_only",
    "policy_block_ip",
    "policy_rate_limit",
    "policy_drop_traffic",
    "policy_isolate_subnet",
    "policy_quarantine_host",
    "policy_temporary_ban",
    "policy_connection_reset",
    "policy_dynamic",
}

STRATEGY_NAMES = {
    "strategy_alert_only",
    "strategy_block_ip",
    "strategy_drop_traffic",
    "strategy_rate_limit",
    "strategy_quarantine_host",
    "strategy_isolate_subnet",
    "strategy_temporary_ban",
    "strategy_connection_reset",
    "strategy_permanent_ban",
}

"""Dynamic policy typed contracts."""

from __future__ import annotations

from nsddos.runtime.policy.contracts_models import (
    PolicyConditionResult,
    PolicyConflictResolution,
    PolicyDiagnostics,
    PolicyEvaluation,
    PolicyHistoryEntry,
    PolicyLearningState,
    PolicyPriority,
    PolicyRollbackState,
    PolicyRule,
    PolicyThresholdState,
)

POLICY_ACTIONS = (
    "alert_only",
    "rate_limit",
    "drop_traffic",
    "block_ip",
    "isolate_subnet",
    "quarantine_host",
    "permanent_ban",
)

POLICY_PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

__all__ = [
    "POLICY_ACTIONS",
    "POLICY_PRIORITIES",
    "PolicyConditionResult",
    "PolicyConflictResolution",
    "PolicyDiagnostics",
    "PolicyEvaluation",
    "PolicyHistoryEntry",
    "PolicyLearningState",
    "PolicyPriority",
    "PolicyRollbackState",
    "PolicyRule",
    "PolicyThresholdState",
]

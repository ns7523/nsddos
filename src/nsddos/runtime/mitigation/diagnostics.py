"""Mitigation diagnostics."""

from __future__ import annotations

from nsddos.runtime.mitigation.registry import default_mitigation_registry


def explain_mitigation() -> dict[str, object]:
    payload = default_mitigation_registry().to_dict()
    payload["target_selection"] = "top_offender_then_ip_sort"
    payload["persistence"] = "latest_plus_history"
    payload["controller_mode"] = "decision_plus_explicit_enforcement"
    return payload

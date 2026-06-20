"""Verification query adapter."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.query.models import RuntimeQuery
from nsddos.runtime.verification.replay import replay_verification_runs
from nsddos.runtime.verification.validators import default_registry


def query_verification(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query validators, categories, dependencies, replay."""
    registry = default_registry()
    rules = registry.ordered_rules()
    replay = replay_verification_runs()
    items = [
        {
            "id": rule.name,
            "name": rule.name,
            "scope": "verification",
            "category": rule.category,
            "dependencies": list(rule.dependencies),
            "degraded_safe": rule.degraded_safe,
        }
        for rule in rules
    ]
    return {
        "items": items,
        "dependencies": [edge.to_dict() for edge in registry.dependencies()],
        "replay": replay,
    }

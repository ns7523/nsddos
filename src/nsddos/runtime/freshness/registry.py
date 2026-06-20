"""Freshness validator registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class FreshnessRegistry:
    validators: dict[str, Callable[[dict[str, object]], dict[str, object]]] = field(default_factory=dict)

    def register(self, scope: str, validator: Callable[[dict[str, object]], dict[str, object]]) -> None:
        self.validators[scope] = validator

    def validate(self, scope: str, payload: dict[str, object]) -> dict[str, object]:
        validator = self.validators.get(scope)
        if not validator:
            raise KeyError(f"unknown freshness scope: {scope}")
        return validator(payload)


def default_freshness_registry() -> FreshnessRegistry:
    from nsddos.runtime.freshness.evidence import validate_evidence_freshness
    from nsddos.runtime.freshness.graph import validate_graph_freshness
    from nsddos.runtime.freshness.replay import validate_replay_freshness
    from nsddos.runtime.freshness.sessions import validate_session_freshness
    from nsddos.runtime.freshness.synchronization import validate_synchronization_freshness

    registry = FreshnessRegistry()
    registry.register("graph", validate_graph_freshness)
    registry.register("replay", validate_replay_freshness)
    registry.register("evidence", validate_evidence_freshness)
    registry.register("session", validate_session_freshness)
    registry.register("synchronization", validate_synchronization_freshness)
    return registry

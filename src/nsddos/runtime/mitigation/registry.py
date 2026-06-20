"""Authoritative mitigation registry."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.runtime.mitigation.contracts import MITIGATION_ACTIONS, POLICY_NAMES, STRATEGY_NAMES


@dataclass(frozen=True)
class MitigationRegistry:
    actions: tuple[str, ...]
    policies: tuple[str, ...]
    strategies: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "actions": list(self.actions),
            "policies": list(self.policies),
            "strategies": list(self.strategies),
        }


def default_mitigation_registry() -> MitigationRegistry:
    return MitigationRegistry(
        actions=tuple(sorted(MITIGATION_ACTIONS)),
        policies=tuple(sorted(POLICY_NAMES)),
        strategies=tuple(sorted(STRATEGY_NAMES)),
    )

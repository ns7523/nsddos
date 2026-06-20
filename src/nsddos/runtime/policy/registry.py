"""Policy registry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PolicyRegistryEntry:
    name: str
    detail: str


@dataclass
class PolicyRegistry:
    entries: dict[str, PolicyRegistryEntry] = field(default_factory=dict)

    def register(self, name: str, detail: str) -> None:
        self.entries[name] = PolicyRegistryEntry(name, detail)

    def lookup(self, name: str) -> PolicyRegistryEntry:
        if name not in self.entries:
            raise KeyError(f"unknown policy registry entry: {name}")
        return self.entries[name]

    def to_dict(self) -> dict[str, object]:
        return {name: entry.detail for name, entry in sorted(self.entries.items())}


def default_policy_registry() -> PolicyRegistry:
    registry = PolicyRegistry()
    registry.register("policy_engine", "dynamic_policy_evaluation")
    registry.register("history_lookup", "runtime.policy.history")
    registry.register("active_policy_lookup", "runtime.policy.latest")
    registry.register("rollback_lookup", "runtime.policy.rollback")
    return registry

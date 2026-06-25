"""Verification validator registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nsddos.runtime.models import VerificationResult
from nsddos.runtime.verification.rules import (
    RuntimeVerificationDependency,
    RuntimeVerificationRule,
)


@dataclass
class VerificationRegistry:
    """Authoritative validator registry with dependency ordering."""

    rules: dict[str, RuntimeVerificationRule] = field(default_factory=dict)

    def register(self, rule: RuntimeVerificationRule) -> None:
        """Register validator rule."""
        if rule.name in self.rules:
            raise ValueError(f"duplicate validator: {rule.name}")
        self.rules[rule.name] = rule

    def dependencies(self) -> list[RuntimeVerificationDependency]:
        """Return dependency edges."""
        edges: list[RuntimeVerificationDependency] = []
        for rule in self.rules.values():
            for dependency in rule.dependencies:
                edges.append(
                    RuntimeVerificationDependency(
                        source=dependency,
                        target=rule.name,
                        reason="validator_dependency",
                    )
                )
        return edges

    def ordered_rules(self) -> list[RuntimeVerificationRule]:
        """Resolve deterministic topological order."""
        ordered: list[RuntimeVerificationRule] = []
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(name: str) -> None:
            if name in permanent:
                return
            if name in temporary:
                raise ValueError(f"verification dependency cycle: {name}")
            if name not in self.rules:
                raise ValueError(f"missing validator dependency: {name}")
            temporary.add(name)
            for dependency in self.rules[name].dependencies:
                visit(dependency)
            temporary.remove(name)
            permanent.add(name)
            ordered.append(self.rules[name])

        for name in sorted(self.rules):
            visit(name)
        return ordered

    def execute_rule(
        self, rule: RuntimeVerificationRule, context: dict[str, Any]
    ) -> list[VerificationResult]:
        """Execute one validator."""
        return rule.validator(context)

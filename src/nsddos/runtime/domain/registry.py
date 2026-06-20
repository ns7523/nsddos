"""Domain registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nsddos.runtime.domain.contracts import ENTITY_TYPES


@dataclass
class DomainRegistry:
    entity_types: set[str] = field(default_factory=lambda: set(ENTITY_TYPES))
    relationship_types: set[str] = field(default_factory=set)
    contract_versions: dict[str, str] = field(default_factory=dict)
    serializers: dict[str, Any] = field(default_factory=dict)
    validators: dict[str, Any] = field(default_factory=dict)


def default_domain_registry() -> DomainRegistry:
    registry = DomainRegistry()
    registry.relationship_types = {
        "topology_relationship",
        "synchronization_relationship",
        "replay_relationship",
        "verification_relationship",
        "evidence_lineage",
        "graph_traversal",
    }
    registry.contract_versions = {entity: "17.0" for entity in registry.entity_types}
    return registry

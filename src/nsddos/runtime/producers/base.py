"""Producer base contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProducerDefinition:
    name: str
    entity_contract: str
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    replay_compatible: bool = True


def producer_metadata(name: str, item_count: int, duration_ms: float) -> dict[str, Any]:
    return {
        "producer": name,
        "item_count": item_count,
        "duration_ms": duration_ms,
        "typed": True,
        "replay_compatible": True,
    }

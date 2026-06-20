"""Domain metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class RuntimeMetadata:
    source: str
    replay_safe: bool = True
    immutable: bool = True
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

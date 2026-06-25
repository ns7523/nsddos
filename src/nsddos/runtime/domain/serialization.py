"""Canonical domain serialization."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from time import monotonic
from typing import Any

from nsddos.runtime.performance import record_timing


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def to_canonical_dict(model: Any) -> dict[str, Any]:
    payload = _normalize(model)
    if not isinstance(payload, dict):
        raise TypeError("domain serialization requires mapping payload")
    return payload


def to_canonical_json(model: Any) -> str:
    start = monotonic()
    payload = json.dumps(
        to_canonical_dict(model), sort_keys=True, separators=(",", ":")
    )
    record_timing("domain.serialization", (monotonic() - start) * 1000)
    return payload

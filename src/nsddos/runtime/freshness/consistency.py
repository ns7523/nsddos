"""Consistency generation and validation."""

from __future__ import annotations

import hashlib
from typing import Any

from nsddos.runtime.domain.serialization import to_canonical_json
from nsddos.runtime.freshness.models import ConsistencyCheck


def consistency_generation(scope: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        f"{scope}:{to_canonical_json(payload)}".encode("utf-8")
    ).hexdigest()
    return digest[:16]


def validate_consistency(scope: str, payload: dict[str, Any]) -> ConsistencyCheck:
    issues: list[str] = []
    if not payload:
        issues.append("empty_payload")
    if (
        scope == "graph"
        and "nodes" not in payload
        and payload.get("type") != "graph-node"
    ):
        issues.append("graph_nodes_missing")
    if (
        scope == "replay"
        and "timestamp" not in payload
        and payload.get("type") != "replay"
    ):
        issues.append("replay_timestamp_missing")
    generation = consistency_generation(scope, payload)
    return ConsistencyCheck(
        scope=scope,
        valid=not issues,
        generation=generation,
        issues=tuple(sorted(issues)),
    )

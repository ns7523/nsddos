"""Deterministic domain identifiers."""

from __future__ import annotations

from hashlib import sha256


def deterministic_id(kind: str, value: str) -> str:
    digest = sha256(f"{kind}:{value}".encode("utf-8")).hexdigest()[:16]
    return f"{kind}:{digest}"


def replay_id(event_type: str, timestamp: str, sequence: int) -> str:
    return deterministic_id("replay", f"{event_type}:{timestamp}:{sequence}")


def evidence_id(reference: str) -> str:
    return deterministic_id("evidence", reference)


def graph_id(node_type: str, name: str) -> str:
    return deterministic_id("graph", f"{node_type}:{name}")


def session_id(owner: str, created_at: str) -> str:
    return deterministic_id("session", f"{owner}:{created_at}")

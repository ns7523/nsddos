"""Freshness validation helpers."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.freshness.contracts import REQUIRED_FRESHNESS_FIELDS


def validate_freshness_payload(payload: dict[str, Any]) -> list[str]:
    return [f"missing:{field}" for field in REQUIRED_FRESHNESS_FIELDS if field not in payload]


def filter_expired(items: list[dict[str, Any]], include_expired: bool = False) -> list[dict[str, Any]]:
    if include_expired:
        return list(items)
    return [item for item in items if item.get("validity_state") != "expired"]

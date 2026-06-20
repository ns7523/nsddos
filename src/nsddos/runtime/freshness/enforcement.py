"""Freshness enforcement layer."""

from __future__ import annotations

from nsddos.runtime.freshness.validation import validate_freshness_payload


def enforce_freshness_contract(payload: dict[str, object]) -> None:
    errors = validate_freshness_payload(payload)
    if errors:
        raise ValueError(f"freshness contract failed: {','.join(errors)}")

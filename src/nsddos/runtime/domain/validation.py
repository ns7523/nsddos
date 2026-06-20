"""Domain validation layer."""

from __future__ import annotations

from time import monotonic
from typing import Any

from nsddos.runtime.performance import record_timing
from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION


REQUIRED_KEYS = ("schema_version", "contract_version")


def validate_contract_payload(payload: dict[str, Any]) -> list[str]:
    start = monotonic()
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in payload:
            errors.append(f"missing:{key}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("contract_version") != CONTRACT_VERSION:
        errors.append("contract_version_mismatch")
    record_timing("domain.validation.contract", (monotonic() - start) * 1000)
    return errors


def validate_identifier_stability(expected: str, observed: str) -> bool:
    return expected == observed


def validate_relationship_integrity(relationships: list[dict[str, Any]], entity_ids: set[str]) -> list[str]:
    start = monotonic()
    errors: list[str] = []
    for item in relationships:
        if item.get("source_id") not in entity_ids:
            errors.append(f"missing_source:{item.get('source_id')}")
        if item.get("target_id") not in entity_ids:
            errors.append(f"missing_target:{item.get('target_id')}")
    record_timing("domain.validation.relationship", (monotonic() - start) * 1000)
    return errors

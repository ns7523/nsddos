"""Legacy isolation adapters -> typed entities."""

from __future__ import annotations

from time import monotonic
from typing import Any

from nsddos.runtime.domain.base import RuntimeRecord
from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.domain.serialization import to_canonical_json
from nsddos.runtime.domain.validation import validate_contract_payload
from nsddos.runtime.freshness.engine import evaluate_freshness
from nsddos.runtime.freshness.enforcement import enforce_freshness_contract
from nsddos.runtime.performance import record_timing
from nsddos.runtime.producers.base import producer_metadata
from nsddos.runtime.producers.models import ProducerEntity, ProducerOutput

SYNTHETIC_TIMESTAMP = "2100-01-01T00:00:00+00:00"


def _observed_timestamp(payload: dict[str, Any]) -> str:
    observed = str(payload.get("observed_at", ""))
    if observed:
        return observed
    timestamp = str(payload.get("timestamp", ""))
    if "T" in timestamp or timestamp.endswith("Z") or "+" in timestamp:
        return timestamp
    return SYNTHETIC_TIMESTAMP


def _as_record(producer: str, item: dict[str, Any], index: int) -> RuntimeRecord:
    payload = dict(item)
    payload.setdefault("schema_version", "1.0")
    payload.setdefault("contract_version", "17.0")
    observed_at = _observed_timestamp(payload)
    payload.setdefault("created_at", observed_at)
    payload.setdefault("observed_at", observed_at)
    payload.setdefault("synchronized_at", observed_at)
    payload.setdefault("replay_only", producer == "replay")
    item_id = str(payload.get("id", deterministic_id("producer-item", f"{producer}:{index}:{to_canonical_json(payload)}")))
    record_type = str(payload.get("type", producer))
    evaluation = evaluate_freshness(producer, payload)
    payload.update(evaluation.freshness.to_dict())
    enforce_freshness_contract(payload)
    errors = validate_contract_payload(payload)
    if errors:
        raise ValueError(f"contract validation failed for {producer}: {','.join(errors)}")
    return RuntimeRecord(record_id=item_id, record_type=record_type, payload=payload)


def produce_records(producer: str, items: list[dict[str, Any]]) -> ProducerOutput:
    start = monotonic()
    entities = tuple(ProducerEntity(producer=producer, record=_as_record(producer, item, index)) for index, item in enumerate(items))
    duration_ms = (monotonic() - start) * 1000
    record_timing(f"producer.{producer}.construction", duration_ms)
    return ProducerOutput(producer=producer, entities=entities, metadata=producer_metadata(producer, len(entities), duration_ms))

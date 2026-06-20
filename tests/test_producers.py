from __future__ import annotations

from dataclasses import FrozenInstanceError

from nsddos.runtime.producers import default_producer_registry, produce_records


def test_producer_determinism() -> None:
    items = [{"id": "a", "type": "node", "value": 1}, {"id": "b", "type": "node", "value": 2}]
    first = produce_records("graph", items)
    second = produce_records("graph", items)
    assert [entity.record.to_dict() for entity in first.entities] == [entity.record.to_dict() for entity in second.entities]


def test_immutability_guarantee() -> None:
    output = produce_records("runtime", [{"id": "x", "type": "runtime"}])
    entity = output.entities[0]
    try:
        entity.producer = "mutated"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("producer entity must be immutable")


def test_replay_reconstruction_integrity() -> None:
    events = [
        {"id": "e2", "type": "replay", "timestamp": "2"},
        {"id": "e1", "type": "replay", "timestamp": "1"},
    ]
    output = produce_records("replay", events)
    assert len(output.entities) == 2
    ids = [item.record.to_dict()["id"] for item in output.entities]
    assert ids == ["e2", "e1"]


def test_producer_dependency_integrity() -> None:
    registry = default_producer_registry()
    ordered = [item.name for item in registry.ordered()]
    assert ordered.index("runtime") < ordered.index("topology")
    assert ordered.index("topology") < ordered.index("datapath")


def test_legacy_adapter_isolation() -> None:
    raw = {"id": "legacy", "type": "legacy_item", "legacy_key": "value"}
    output = produce_records("collection", [raw])
    typed = output.entities[0].record.to_dict()
    assert typed["legacy_key"] == "value"
    assert typed["schema_version"] == "1.0"
    assert typed["contract_version"] == "17.0"


def test_typed_pipeline_integrity() -> None:
    output = produce_records("analysis", [{"id": "typed", "type": "analysis_item"}])
    payload = output.entities[0].record.to_dict()
    assert payload["id"] == "typed"
    assert payload["type"] == "analysis_item"


def test_serialization_contract_enforcement() -> None:
    output = produce_records("verification", [{"id": "v1", "type": "validator"}])
    payload = output.entities[0].record.to_dict()
    assert payload["schema_version"] == "1.0"
    assert payload["contract_version"] == "17.0"

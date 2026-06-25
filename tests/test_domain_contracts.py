from __future__ import annotations

from nsddos.runtime.domain.evidence import RuntimeEvidence
from nsddos.runtime.domain.graph import RuntimeEntity
from nsddos.runtime.domain.identifiers import (
    deterministic_id,
    evidence_id,
    graph_id,
    replay_id,
    session_id,
)
from nsddos.runtime.domain.registry import default_domain_registry
from nsddos.runtime.domain.replay import (
    reconstruct_replay,
    validate_replay_compatibility,
)
from nsddos.runtime.domain.relationships import RuntimeRelationship
from nsddos.runtime.domain.serialization import to_canonical_dict, to_canonical_json
from nsddos.runtime.domain.validation import (
    validate_contract_payload,
    validate_identifier_stability,
    validate_relationship_integrity,
)
from nsddos.runtime.domain.versions import MIGRATION_METADATA


def test_identifier_stability() -> None:
    assert deterministic_id("x", "y") == deterministic_id("x", "y")
    assert replay_id("phase", "ts", 1) == replay_id("phase", "ts", 1)
    assert evidence_id("ref") == evidence_id("ref")
    assert graph_id("node", "A") == graph_id("node", "A")
    assert session_id("owner", "now") == session_id("owner", "now")
    assert validate_identifier_stability("a", "a")


def test_schema_and_contract_validation() -> None:
    assert (
        validate_contract_payload({"schema_version": "1.0", "contract_version": "17.0"})
        == []
    )
    assert "schema_version_mismatch" in validate_contract_payload(
        {"schema_version": "2.0", "contract_version": "17.0"}
    )


def test_serialization_determinism() -> None:
    payload = {"b": 2, "a": {"y": 2, "x": 1}}
    first = to_canonical_json(payload)
    second = to_canonical_json(payload)
    assert first == second
    assert to_canonical_dict(payload)["a"]["x"] == 1


def test_replay_compatibility() -> None:
    replay = reconstruct_replay(
        [
            {
                "replay_id": "r1",
                "event_type": "a",
                "timestamp": "2",
                "status": "pass",
                "message": "ok",
            },
            {
                "replay_id": "r2",
                "event_type": "b",
                "timestamp": "1",
                "status": "pass",
                "message": "ok",
            },
        ]
    )
    assert len(replay.events) == 2
    assert validate_replay_compatibility(replay) == []


def test_relationship_and_graph_integrity() -> None:
    entities = (
        RuntimeEntity(entity_id="n1", entity_type="switch", label="n1"),
        RuntimeEntity(entity_id="n2", entity_type="host", label="n2"),
    )
    relationships = [
        RuntimeRelationship(
            relationship_type="link", source_id="n1", target_id="n2"
        ).to_dict(),
    ]
    assert (
        validate_relationship_integrity(
            relationships, {item.entity_id for item in entities}
        )
        == []
    )


def test_evidence_lineage_integrity() -> None:
    evidence = RuntimeEvidence(
        evidence_id="e1", reference="snapshot", lineage=("verification", "replay")
    )
    payload = evidence.to_dict()
    assert payload["lineage"] == ("verification", "replay")


def test_migration_compatibility_metadata() -> None:
    assert MIGRATION_METADATA["schema"] == "1.0"
    assert MIGRATION_METADATA["contract"] == "17.0"
    assert MIGRATION_METADATA["replay_compatibility"] == "1.x"


def test_domain_registry_has_contracts() -> None:
    registry = default_domain_registry()
    assert "RuntimeGraph" in registry.entity_types
    assert "evidence_lineage" in registry.relationship_types

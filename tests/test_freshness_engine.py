from __future__ import annotations

from datetime import datetime, timedelta, timezone

from nsddos.runtime.freshness.consistency import (
    consistency_generation,
    validate_consistency,
)
from nsddos.runtime.freshness.engine import evaluate_freshness
from nsddos.runtime.freshness.lineage import propagate_state
from nsddos.runtime.freshness.validation import (
    filter_expired,
    validate_freshness_payload,
)
from nsddos.runtime.query.engine import execute_query
from nsddos.runtime.query.models import RuntimeQuery


def _iso(delta_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)).isoformat()


def test_freshness_valid_and_expired_states() -> None:
    valid = evaluate_freshness(
        "telemetry",
        {"created_at": _iso(-5), "observed_at": _iso(-5), "synchronized_at": _iso(-1)},
    )
    expired = evaluate_freshness(
        "telemetry",
        {
            "created_at": _iso(-500),
            "observed_at": _iso(-500),
            "synchronized_at": _iso(-500),
        },
    )
    assert valid.freshness.validity_state == "valid"
    assert expired.freshness.validity_state == "expired"


def test_stale_inheritance_propagation() -> None:
    assert propagate_state("stale", "valid") == "stale"
    assert propagate_state("expired", "valid") == "degraded"


def test_replay_only_state() -> None:
    replay = evaluate_freshness(
        "replay",
        {
            "created_at": _iso(-100),
            "observed_at": _iso(-100),
            "synchronized_at": _iso(-50),
            "replay_only": True,
        },
    )
    assert replay.freshness.validity_state == "replay_only"


def test_consistency_generation_determinism() -> None:
    payload = {"id": "n1", "type": "graph-node"}
    assert consistency_generation("graph", payload) == consistency_generation(
        "graph", payload
    )
    check = validate_consistency("graph", payload)
    assert check.valid


def test_freshness_contract_validation() -> None:
    errors = validate_freshness_payload({"created_at": _iso()})
    assert "missing:observed_at" in errors


def test_query_freshness_filtering_excludes_expired(tmp_path, monkeypatch) -> None:
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import snapshots as snapshots_module
    from nsddos.runtime.persistence import atomic_write_json

    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    atomic_write_json(
        snapshot_dir / "snapshot-1.json",
        {
            "timestamp": _iso(-10),
            "created_at": _iso(-10),
            "observed_at": _iso(-10),
            "synchronized_at": _iso(-10),
            "convergence_state": {"status": "converged"},
            "runtime_profile": {"name": "linux-native"},
        },
    )
    monkeypatch.setattr(snapshots_module, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")

    result = execute_query({}, RuntimeQuery(name="snapshots", scope="persistence"))
    assert result.freshness["expired_filtered"] >= 0


def test_filter_expired_items() -> None:
    items = [
        {"id": "a", "validity_state": "valid"},
        {"id": "b", "validity_state": "expired"},
    ]
    assert [item["id"] for item in filter_expired(items)] == ["a"]

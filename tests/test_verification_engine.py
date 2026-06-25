from __future__ import annotations

from nsddos.runtime.models import VerificationResult
from nsddos.runtime.verification.registry import VerificationRegistry
from nsddos.runtime.verification.replay import (
    persist_verification_execution,
    replay_verification_runs,
)
from nsddos.runtime.verification.results import (
    VerificationCategoryResult,
    VerificationExecutionResult,
    VerificationEvidenceReference,
)
from nsddos.runtime.verification.rules import RuntimeVerificationRule
from nsddos.runtime.verification.severity import severity_for_status, worst_severity
from nsddos.runtime.verification.validators import default_registry


def _validator(name: str, status: str = "pass"):
    def inner(context):
        return [VerificationResult(name, status, name, "test")]

    return inner


def test_registry_orders_validators_by_dependencies():
    registry = VerificationRegistry()
    registry.register(
        RuntimeVerificationRule("last", "test", _validator("last"), ("middle",))
    )
    registry.register(RuntimeVerificationRule("first", "test", _validator("first")))
    registry.register(
        RuntimeVerificationRule("middle", "test", _validator("middle"), ("first",))
    )

    assert [rule.name for rule in registry.ordered_rules()] == [
        "first",
        "middle",
        "last",
    ]


def test_default_registry_has_required_categories():
    registry = default_registry()
    categories = {rule.category for rule in registry.ordered_rules()}

    assert {
        "environment",
        "collection",
        "reconciliation",
        "convergence",
        "integrity",
        "detection",
        "ml",
        "policy",
        "mitigation",
        "deployment",
        "distributed",
        "dashboard",
        "release",
        "live",
        "simulation",
        "streaming",
    } <= categories
    assert registry.dependencies()


def test_mitigation_validator_order_is_after_detection():
    registry = default_registry()
    ordered = [rule.name for rule in registry.ordered_rules()]

    assert (
        ordered.index("live_provider")
        < ordered.index("simulation")
        < ordered.index("streaming")
        < ordered.index("detection")
        < ordered.index("ml")
        < ordered.index("policy")
        < ordered.index("mitigation")
        < ordered.index("deployment")
        < ordered.index("distributed")
        < ordered.index("dashboard")
        < ordered.index("release")
        < ordered.index("integrity")
    )


def test_severity_model_is_deterministic():
    assert severity_for_status("pass") == "info"
    assert severity_for_status("warn") == "warning"
    assert severity_for_status("stale") == "degraded"
    assert severity_for_status("fail") == "failed"
    assert worst_severity(["info", "failed", "warning"]) == "failed"


def test_category_result_derives_worst_severity():
    category = VerificationCategoryResult(
        "runtime",
        results=[
            VerificationResult("ok", "pass", "", "runtime"),
            VerificationResult("bad", "fail", "", "runtime"),
        ],
    )

    assert category.severity == "failed"
    assert category.to_dict()["severity"] == "failed"


def test_execution_result_attaches_evidence_and_schema():
    execution = VerificationExecutionResult(
        run_id="run-1",
        timestamp="now",
        results=[VerificationResult("ok", "pass", "", "runtime")],
        evidence=[VerificationEvidenceReference("snapshot", "snapshot.json")],
    )

    payload = execution.to_dict()
    assert payload["schema_version"] == "1.0"
    assert payload["evidence"][0]["kind"] == "snapshot"
    assert payload["severity"] == "info"


def test_verification_replay_persists_and_compares_runs(tmp_path, monkeypatch):
    from nsddos.runtime.verification import replay as replay_module

    monkeypatch.setattr(replay_module, "VERIFICATION_DIR", tmp_path)
    persist_verification_execution(
        VerificationExecutionResult(
            run_id="a",
            timestamp="1",
            results=[VerificationResult("x", "fail", "", "runtime")],
        ).to_dict()
    )
    persist_verification_execution(
        VerificationExecutionResult(
            run_id="b",
            timestamp="2",
            results=[VerificationResult("x", "fail", "", "runtime")],
        ).to_dict()
    )

    replay = replay_verification_runs()

    assert replay["run_count"] == 2
    assert replay["repeated_failures"]["x"] == 2
    assert replay["transitions"][0]["from"] == "failed"


def test_registry_rejects_missing_dependency():
    registry = VerificationRegistry()
    registry.register(
        RuntimeVerificationRule("needs-missing", "test", _validator("x"), ("missing",))
    )

    try:
        registry.ordered_rules()
    except ValueError as exc:
        assert "missing validator dependency" in str(exc)
    else:
        raise AssertionError("missing dependency must fail")

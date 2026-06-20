from __future__ import annotations

from nsddos.release import generate_release_candidate, validate_release_candidate


def _patch_release_sources(monkeypatch):
    from nsddos.release import packaging as packaging_module

    monkeypatch.setattr(
        packaging_module,
        "latest_deployment_payload",
        lambda: {
            "deployment_state": "dry_run_ready",
            "service_health": "healthy",
            "rollback_available": True,
            "diagnostics": {"missing_secret_count": 0},
            "secret_contract": {"missing_keys": []},
        },
    )
    monkeypatch.setattr(
        packaging_module,
        "latest_distributed_evaluation",
        lambda: {"active_nodes": 2, "cluster_health": "healthy"},
    )
    monkeypatch.setattr(
        packaging_module,
        "latest_dashboard_evaluation",
        lambda: {
            "dashboard_health": "healthy",
            "active_alerts": 1,
            "stream_throughput": 32.0,
            "ml_confidence": 0.84,
            "policy_events": 12,
            "mitigation_events": 3,
        },
    )
    monkeypatch.setattr(
        packaging_module,
        "replay_verification_runs",
        lambda limit=1: {"runs": [{"results": [{"status": "pass"}, {"status": "warn"}]}]},
    )
    monkeypatch.setattr(
        packaging_module,
        "detect_runtime_profile",
        lambda: {"name": "linux-native"},
    )


def test_release_benchmark_and_scores(monkeypatch, tmp_path):
    from nsddos.release import packaging as packaging_module
    from nsddos.release import registry as registry_module

    release_dir = tmp_path / "release"
    monkeypatch.setattr(packaging_module, "RELEASE_DIR", release_dir)
    monkeypatch.setattr(registry_module, "RELEASE_DIR", release_dir)
    _patch_release_sources(monkeypatch)

    evaluation = generate_release_candidate({"release": {"version": "1.0.0-rc1"}})

    assert evaluation.release_version == "1.0.0-rc1"
    assert evaluation.benchmark_score > 0.0
    assert evaluation.load_test_score > 0.0
    assert evaluation.stress_test_score > 0.0
    assert evaluation.chaos.scenarios
    assert evaluation.fault_injection.scenarios
    assert not validate_release_candidate(evaluation)


def test_release_persists_expected_files(monkeypatch, tmp_path):
    from nsddos.release import packaging as packaging_module
    from nsddos.release import registry as registry_module

    release_dir = tmp_path / "release"
    monkeypatch.setattr(packaging_module, "RELEASE_DIR", release_dir)
    monkeypatch.setattr(registry_module, "RELEASE_DIR", release_dir)
    _patch_release_sources(monkeypatch)

    generate_release_candidate({"release": {"version": "1.0.0-rc1"}})

    assert (release_dir / "latest.json").exists()
    assert (release_dir / "benchmark.json").exists()
    assert (release_dir / "artifacts.json").exists()
    assert (release_dir / "package.json").exists()
    assert (release_dir / "release_notes.json").exists()
    assert (release_dir / "diagnostics.json").exists()
    assert any(path.name.startswith("release-") for path in release_dir.iterdir())


def test_release_dependency_and_security_audit(monkeypatch, tmp_path):
    from nsddos.release import packaging as packaging_module
    from nsddos.release import registry as registry_module

    release_dir = tmp_path / "release"
    monkeypatch.setattr(packaging_module, "RELEASE_DIR", release_dir)
    monkeypatch.setattr(registry_module, "RELEASE_DIR", release_dir)
    _patch_release_sources(monkeypatch)

    evaluation = generate_release_candidate({"release": {"version": "1.0.0-rc1"}})

    assert evaluation.dependencies.package_count >= 1
    assert evaluation.dependencies.dependency_health in {"healthy", "degraded"}
    assert evaluation.security_audit.security_score >= 0.0


def test_release_validation_failure_path():
    from datetime import datetime, timezone

    from nsddos.release.contracts import ReleaseCandidateEvaluation

    evaluation = ReleaseCandidateEvaluation(
        release_id="release:x",
        release_version="1.0.0-rc1",
        benchmark_score=1.2,
        load_test_score=0.5,
        stress_test_score=0.5,
        security_score=0.5,
        dependency_health="invalid",
        performance_score=0.5,
        hardening_state="bad",
        compliance_state="bad",
        release_state="bad",
        timestamp=datetime.now(timezone.utc),
    )

    errors = validate_release_candidate(evaluation)

    assert "benchmark_corruption" in errors
    assert "dependency_audit_failure" in errors
    assert "release_package_corruption" in errors

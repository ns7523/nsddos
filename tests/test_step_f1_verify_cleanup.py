from __future__ import annotations

import json

from nsddos.runtime.flows import telemetry_freshness
from nsddos.runtime.verification.validators import (
    validate_live_provider_contracts,
    validate_simulation_contracts,
    validate_streaming_contracts,
)


def test_telemetry_freshness_sets_timestamp_when_flows_exist(monkeypatch):
    class FakeProvider:
        def __init__(self, api_url: str):
            self.api_url = api_url

        def is_reachable(self) -> bool:
            return True

        def flows(self):
            return [{"flowID": 1, "dataSource": "17"}]

    monkeypatch.setattr("nsddos.runtime.flows.SFlowProvider", FakeProvider)
    freshness = telemetry_freshness({"api_port": 8008}, interval=0.0)
    assert freshness.last_flow_timestamp
    assert freshness.stale is False


def test_disabled_optional_validators_are_pass():
    context = {
        "config": {
            "runtime": {
                "live": {"enabled": False},
                "simulation": {"source_enabled": False},
                "streaming": {"enabled": False},
            }
        }
    }
    assert [item.status for item in validate_live_provider_contracts(context)] == [
        "pass",
        "pass",
    ]
    assert [item.status for item in validate_simulation_contracts(context)] == [
        "pass",
        "pass",
    ]
    assert [item.status for item in validate_streaming_contracts(context)] == [
        "pass",
        "pass",
    ]


def test_secret_contract_requires_real_environment_secrets(monkeypatch, tmp_path):
    from nsddos.deployment import secrets as secrets_module

    example = tmp_path / ".env.example"
    example.write_text(
        "NSDDOS_API_TOKEN=local-dev-token\nNSDDOS_SECRET_KEY=local-dev-secret-key\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("NSDDOS_API_TOKEN", raising=False)
    monkeypatch.delenv("NSDDOS_SECRET_KEY", raising=False)
    contract = secrets_module.build_secret_contract()
    assert contract.missing_keys == ("NSDDOS_API_TOKEN", "NSDDOS_SECRET_KEY")


def test_dependency_audit_accepts_bounded_ranges(tmp_path):
    from nsddos.release.dependencies import audit_dependencies

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "\n".join(
            [
                "[project]",
                "dependencies = [",
                '  "fastapi>=0.115,<1.0",',
                '  "uvicorn>=0.30,<1.0",',
                "]",
            ]
        ),
        encoding="utf-8",
    )
    result = audit_dependencies(tmp_path)
    assert result.dependency_health == "healthy"


def test_release_candidate_local_healthy_mode_is_release_ready(monkeypatch, tmp_path):
    from nsddos.release import packaging as packaging_module
    from nsddos.release import registry as registry_module

    release_dir = tmp_path / "release"
    monkeypatch.setattr(packaging_module, "RELEASE_DIR", release_dir)
    monkeypatch.setattr(registry_module, "RELEASE_DIR", release_dir)
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
        lambda: {"active_nodes": 1, "cluster_health": "healthy"},
    )
    monkeypatch.setattr(
        packaging_module,
        "latest_dashboard_evaluation",
        lambda: {
            "dashboard_health": "healthy",
            "active_alerts": 0,
            "stream_throughput": 32.0,
            "ml_confidence": 0.84,
            "policy_events": 12,
            "mitigation_events": 3,
        },
    )
    monkeypatch.setattr(
        packaging_module,
        "replay_verification_runs",
        lambda limit=1: {"runs": [{"results": [{"status": "pass"}]}]},
    )
    monkeypatch.setattr(
        packaging_module,
        "detect_runtime_profile",
        lambda: {"name": "docker-linux"},
    )
    evaluation = packaging_module.generate_release_candidate(
        {"release": {"version": "1.0.0-rc1"}}
    )
    assert evaluation.release_state == "release_ready"


def test_distributed_local_node_stays_healthy_on_warning_history(monkeypatch, tmp_path):
    from nsddos.distributed import discovery as discovery_module

    verification_dir = tmp_path / "runtime" / "verification"
    verification_dir.mkdir(parents=True)
    (verification_dir / "verification-1-warning.json").write_text(
        json.dumps({"run_id": "warning", "severity": "warning", "results": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        discovery_module,
        "latest_deployment_payload",
        lambda: {"container_contracts": [{"name": "detector"}]},
    )
    monkeypatch.setattr(
        discovery_module,
        "socket",
        type("SocketStub", (), {"gethostname": staticmethod(lambda: "localhost")}),
    )
    monkeypatch.setattr(
        discovery_module,
        "replay_verification_runs",
        lambda limit=1: {"runs": [{"severity": "warning"}]},
    )

    nodes = discovery_module.discover_candidate_nodes(
        {"distributed": {"local_node_id": "local-node"}}
    )

    assert len(nodes) == 1
    assert nodes[0]["state"] == "healthy"

from __future__ import annotations

from pathlib import Path

from nsddos.deployment import (
    deploy_runtime_stack,
    rollback_runtime_stack,
    validate_deployment_evaluation,
)


def test_deployment_generation_is_deterministic_shape(monkeypatch, tmp_path):
    from nsddos.deployment import orchestration as orchestration_module

    monkeypatch.setattr(orchestration_module, "DEPLOYMENT_DIR", tmp_path / "deployment")
    evaluation = deploy_runtime_stack(
        {"api_port": 8008, "dashboard_port": 3000, "lab": {"floodlight_port": 8080}}
    )

    assert evaluation.environment == "prod"
    assert len(evaluation.container_contracts) == 3
    assert evaluation.networking_contract.external_ports == ("3000/tcp", "8008/tcp")
    assert evaluation.rolling_update.batch_size >= 1
    assert not validate_deployment_evaluation(evaluation)


def test_deployment_persists_latest_and_history(monkeypatch, tmp_path):
    from nsddos.deployment import orchestration as orchestration_module

    deployment_dir = tmp_path / "deployment"
    monkeypatch.setattr(orchestration_module, "DEPLOYMENT_DIR", deployment_dir)
    evaluation = deploy_runtime_stack(
        {"api_port": 8008, "dashboard_port": 3000, "lab": {"floodlight_port": 8080}}
    )

    assert (deployment_dir / "latest.json").exists()
    assert (deployment_dir / "backup.json").exists()
    assert (deployment_dir / "rollback.json").exists()
    assert (deployment_dir / "diagnostics.json").exists()
    assert any(path.name.startswith("deployment-") for path in deployment_dir.iterdir())
    assert evaluation.rollback_state.rollback_available is True


def test_deployment_rollback_sets_rollback_state(monkeypatch, tmp_path):
    from nsddos.deployment import orchestration as orchestration_module

    monkeypatch.setattr(orchestration_module, "DEPLOYMENT_DIR", tmp_path / "deployment")
    evaluation = rollback_runtime_stack(
        {"api_port": 8008, "dashboard_port": 3000, "lab": {"floodlight_port": 8080}}
    )

    assert evaluation.deployment_state == "rollback_planned"
    assert evaluation.rollback_state.rollback_id.startswith("rollback-")


def test_invalid_deployment_rejected_when_manifest_list_missing():
    from nsddos.deployment.contracts import (
        AutoscalingPolicy,
        BackupSnapshot,
        ContainerContract,
        DeploymentDiagnostics,
        DeploymentEvaluation,
        DeploymentHealthState,
        NetworkingContract,
        RecoveryState,
        RollingUpdatePlan,
        RollbackState,
        SecretContract,
        ServiceMeshContract,
    )

    evaluation = DeploymentEvaluation(
        deployment_id="deploy-x",
        environment="prod",
        container_contracts=(ContainerContract(name="x", image="y", command="z"),),
        secret_contract=SecretContract(required_keys=()),
        networking_contract=NetworkingContract(
            external_ports=(), internal_ports=(), network_policies=(), service_names=()
        ),
        service_mesh=ServiceMeshContract(services=("x",), dependencies=()),
        health=DeploymentHealthState(
            state="healthy",
            service_health="healthy",
            environment_ready=True,
            docker_installed=True,
            docker_daemon_running=True,
            compose_available=True,
            detail="ok",
        ),
        autoscaling_policy=AutoscalingPolicy(1, 3, 70, 75, 500),
        rolling_update=RollingUpdatePlan(
            "rolling", 1, 0, ("health_checks",), ("failed_health",)
        ),
        backup_snapshot=BackupSnapshot("b", (), str(Path("/tmp")), True, "t"),
        recovery_state=RecoveryState("healthy", (), True, "ok"),
        rollback_state=RollbackState("r", True, "v1", ("restore",), "ok", "t"),
        diagnostics=DeploymentDiagnostics(1.0, "low", 0, True, True, 0),
        manifests=(),
        created_at="t",
    )

    assert "missing_manifests" in validate_deployment_evaluation(evaluation)

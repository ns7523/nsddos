from __future__ import annotations

from nsddos.distributed import (
    orchestrate_cluster_runtime,
    validate_distributed_evaluation,
)


def _config() -> dict:
    return {
        "distributed": {
            "local_node_id": "node-local",
            "replication_factor": 2,
            "partition_count": 4,
            "election_timeout_seconds": 5,
            "nodes": [
                {
                    "node_id": "node-1",
                    "hostname": "node-1.local",
                    "roles": ["control", "runtime"],
                    "capabilities": ["runtime", "streaming", "ml"],
                    "worker_capacity": 5,
                },
                {
                    "node_id": "node-2",
                    "hostname": "node-2.local",
                    "roles": ["runtime"],
                    "capabilities": ["runtime", "policy", "mitigation"],
                    "worker_capacity": 5,
                },
            ],
        }
    }


def test_deterministic_node_discovery_and_election(monkeypatch, tmp_path):
    from nsddos.distributed import orchestrator as orchestrator_module
    from nsddos.distributed import checkpoint as checkpoint_module

    monkeypatch.setattr(
        orchestrator_module, "DISTRIBUTED_DIR", tmp_path / "distributed"
    )
    monkeypatch.setattr(checkpoint_module, "DISTRIBUTED_DIR", tmp_path / "distributed")
    evaluation = orchestrate_cluster_runtime(_config())

    assert evaluation.active_nodes == 2
    assert evaluation.leader_node == "node-1"
    assert evaluation.leader_state.standby_node == "node-2"
    assert not validate_distributed_evaluation(evaluation)


def test_worker_assignment_and_partition_stability(monkeypatch, tmp_path):
    from nsddos.distributed import orchestrator as orchestrator_module
    from nsddos.distributed import checkpoint as checkpoint_module

    monkeypatch.setattr(
        orchestrator_module, "DISTRIBUTED_DIR", tmp_path / "distributed"
    )
    monkeypatch.setattr(checkpoint_module, "DISTRIBUTED_DIR", tmp_path / "distributed")
    evaluation = orchestrate_cluster_runtime(_config())

    assert evaluation.worker_count == 5
    assert evaluation.partition_count == 4
    assert evaluation.partition_assignments[0].partition_id == "partition-1"
    assert evaluation.partition_assignments[0].node_id == "node-1"
    assert evaluation.replication_factor == 2


def test_checkpoint_persistence_and_failover_plan(monkeypatch, tmp_path):
    from nsddos.distributed import orchestrator as orchestrator_module
    from nsddos.distributed import checkpoint as checkpoint_module

    distributed_dir = tmp_path / "distributed"
    monkeypatch.setattr(orchestrator_module, "DISTRIBUTED_DIR", distributed_dir)
    monkeypatch.setattr(checkpoint_module, "DISTRIBUTED_DIR", distributed_dir)
    evaluation = orchestrate_cluster_runtime(_config())

    assert (distributed_dir / "latest.json").exists()
    assert (distributed_dir / "checkpoint.json").exists()
    assert (distributed_dir / "registry.json").exists()
    assert (distributed_dir / "diagnostics.json").exists()
    assert evaluation.failover_available is True
    assert evaluation.failover_state.leader_failover_node in {"node-1", "node-2"}


def test_rebalance_plan_generation_for_failed_node(monkeypatch, tmp_path):
    from nsddos.distributed import orchestrator as orchestrator_module
    from nsddos.distributed import checkpoint as checkpoint_module

    config = _config()
    config["distributed"]["nodes"][1]["state"] = "failed"
    distributed_dir = tmp_path / "distributed"
    monkeypatch.setattr(orchestrator_module, "DISTRIBUTED_DIR", distributed_dir)
    monkeypatch.setattr(checkpoint_module, "DISTRIBUTED_DIR", distributed_dir)
    evaluation = orchestrate_cluster_runtime(config)

    assert evaluation.rebalance_plan.required is True
    assert evaluation.cluster_health == "degraded"
    assert "node-2" in evaluation.failover_state.failed_nodes


def test_invalid_cluster_rejection_when_duplicate_node_ids(monkeypatch, tmp_path):
    from nsddos.distributed import orchestrator as orchestrator_module
    from nsddos.distributed import checkpoint as checkpoint_module

    config = _config()
    config["distributed"]["nodes"][1]["node_id"] = "node-1"
    monkeypatch.setattr(
        orchestrator_module, "DISTRIBUTED_DIR", tmp_path / "distributed"
    )
    monkeypatch.setattr(checkpoint_module, "DISTRIBUTED_DIR", tmp_path / "distributed")

    try:
        orchestrate_cluster_runtime(config)
    except ValueError as exc:
        assert "duplicate_node_registration" in str(exc)
    else:
        raise AssertionError("duplicate node ids must fail")

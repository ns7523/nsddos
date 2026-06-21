"""Configuration bootstrap and YAML loading."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from nsddos.constants import CONFIG_PATH, RUNTIME_DIRECTORIES, STATE_PATH
from nsddos.runtime.models import RuntimeState
from nsddos.runtime.persistence import atomic_write_json, recover_json

DEFAULT_CONFIG: dict[str, Any] = {
    "dashboard_port": 3000,
    "sflow_port": 6343,
    "api_port": 8008,
    "lab": {
        "floodlight_port": 8080,
        "controller_port": 6653,
        "detector_port": 9000,
        "mininet_topology": "single,3",
        "ovs_bridge": "s1",
        "ovs_sflow_target": "127.0.0.1:6343",
        "ovs_agent_interface": "lo",
        "ovs_sampling": 10,
        "ovs_polling": 20,
    },
    "simulation": {
        "enabled": True,
    },
    "logging": {
        "level": "INFO",
    },
    "ml": {
        "model": "default.pkl",
    },
    "release": {
        "version": "1.0.0-rc1",
        "load_event_count": 10000,
        "api_burst_count": 250,
        "stream_burst_count": 256,
        "provider_burst_count": 128,
        "benchmark_min_score": 0.70,
        "security_min_score": 0.80,
        "performance_min_score": 0.70,
        "stress_min_score": 0.65,
        "artifact_prefix": "nsddos-release",
        "checksum_algorithm": "sha256",
    },
    "runtime": {
        "live": {
            "enabled": False,
            "poll_interval_seconds": 1,
            "timeout_seconds": 3,
            "retry_count": 1,
            "buffer_batch_size": 3,
            "providers": {
                "sflowrt": {
                    "endpoint": "http://127.0.0.1:8008",
                },
                "floodlight": {
                    "endpoint": "http://127.0.0.1:8080",
                },
                "mininet": {
                    "controller_host": "127.0.0.1",
                    "controller_port": 6653,
                },
                "ovs": {
                    "bridge": "s1",
                    "collector_target": "127.0.0.1:6343",
                    "agent_interface": "lo",
                },
            },
        },
        "simulation": {
            "enabled": True,
            "source_enabled": False,
            "default_attack_type": "syn_flood",
            "default_duration_seconds": 10,
            "default_intensity_level": "medium",
            "default_replay_mode": False,
            "scheduler": {
                "start_delay_seconds": 0,
                "repeat_interval_seconds": 0,
            },
            "targets": {
                "default_kind": "host",
            },
        },
        "streaming": {
            "enabled": False,
            "batch_size": 64,
            "max_queue_depth": 1024,
            "max_buffer_size": 256,
            "window_seconds": 10,
            "window_kind": "sliding",
            "checkpoint_every_events": 50,
            "overflow_policy": "drop_oldest",
            "source_precedence": "live_first",
        },
        "policy": {
            "enabled": True,
            "history_limit": 100,
        },
        "ml": {
            "enabled": True,
            "model_family": "random_forest_style",
            "retrain_threshold": 0.35,
            "dataset_limit": 256,
            "history_limit": 100,
            "drift_threshold": 0.30,
            "false_positive_threshold": 0.20,
        },
    },
    "distributed": {
        "enabled": True,
        "local_node_id": "local-node",
        "replication_factor": 2,
        "partition_count": 0,
        "election_timeout_seconds": 5,
        "nodes": [],
    },
}


def _deep_merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge nested config with defaults."""
    merged: dict[str, Any] = dict(defaults)
    for key, value in overrides.items():
        if (
            isinstance(value, dict)
            and isinstance(merged.get(key), dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def ensure_runtime_directories() -> tuple[Path, ...]:
    """Create runtime directory tree if missing."""
    for path in RUNTIME_DIRECTORIES:
        path.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIRECTORIES


def ensure_default_config(config_path: Path = CONFIG_PATH) -> Path:
    """Create default YAML config if missing."""
    ensure_runtime_directories()
    if not config_path.exists():
        with config_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(DEFAULT_CONFIG, file, sort_keys=False)
    return config_path


def load_config(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load configuration from YAML file."""
    path = ensure_default_config(config_path)
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return _deep_merge(DEFAULT_CONFIG, data)


def ensure_runtime_state() -> Path:
    """Create default runtime state file if missing."""
    ensure_runtime_directories()
    if not STATE_PATH.exists():
        write_runtime_state(RuntimeState())
    return STATE_PATH


def load_runtime_state() -> RuntimeState:
    """Load runtime state JSON."""
    path = ensure_runtime_state()
    payload = recover_json(path, RuntimeState().to_dict())
    return RuntimeState.from_dict(payload)


def write_runtime_state(state: RuntimeState | dict[str, Any]) -> Path:
    """Persist runtime state JSON."""
    ensure_runtime_directories()
    payload = state.to_dict() if isinstance(state, RuntimeState) else state
    atomic_write_json(STATE_PATH, payload)
    return STATE_PATH


def build_runtime_state(
    stack_running: bool,
    services: list[Any] | None = None,
    provider_status: dict[str, dict[str, Any]] | None = None,
    topology_state: str = "stopped",
    topology_pid: int | None = None,
    last_error: str | None = None,
) -> RuntimeState:
    """Build runtime state payload."""
    timestamp = datetime.now(timezone.utc).isoformat()
    return RuntimeState(
        stack_running=stack_running,
        started_at=timestamp if stack_running else None,
        updated_at=timestamp,
        stopped_at=None if stack_running else timestamp,
        services=services or [],
        provider_status=provider_status or {},
        topology_state=topology_state,
        topology_pid=topology_pid,
        last_error=last_error,
    )

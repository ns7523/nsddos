"""Service capabilities."""

from __future__ import annotations

from nsddos.runtime.capabilities import detect_runtime_capabilities


def detect_service_capabilities(config: dict) -> dict:
    runtime = detect_runtime_capabilities().to_dict()
    return {
        "daemon_support": True,
        "replay_support": True,
        "synchronization_support": True,
        "degraded_runtime_support": True,
        "streaming_support": True,
        "runtime_capabilities": runtime,
    }

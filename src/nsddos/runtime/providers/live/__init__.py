"""Live provider integration subsystem."""

from nsddos.runtime.providers.live.diagnostics import build_provider_diagnostics
from nsddos.runtime.providers.live.discovery import discover_runtime_providers
from nsddos.runtime.providers.live.health import collect_provider_health
from nsddos.runtime.providers.live.telemetry import (
    collect_live_telemetry,
    live_snapshot_to_collection_state,
    snapshot_to_detection_telemetry,
)

__all__ = [
    "collect_live_telemetry",
    "collect_provider_health",
    "discover_runtime_providers",
    "build_provider_diagnostics",
    "live_snapshot_to_collection_state",
    "snapshot_to_detection_telemetry",
]

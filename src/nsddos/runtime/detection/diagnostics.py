"""Detection diagnostics."""

from __future__ import annotations

from nsddos.runtime.detection.anomaly import build_baseline
from nsddos.runtime.detection.registry import default_detection_registry


def explain_detection() -> dict[str, object]:
    registry = default_detection_registry()
    _, baseline_source = build_baseline()
    payload = registry.to_dict()
    payload["baseline_source"] = baseline_source
    return payload

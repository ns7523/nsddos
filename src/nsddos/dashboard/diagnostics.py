"""Dashboard diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.dashboard.contracts import (
    DashboardDiagnostics,
    DashboardSourceBundle,
    VisualizationSeries,
)


def build_dashboard_diagnostics(
    sources: DashboardSourceBundle,
    visualizations: tuple[VisualizationSeries, ...],
) -> DashboardDiagnostics:
    """Compute diagnostics summary."""
    start = datetime.now(timezone.utc)
    missing = []
    if not sources.detection:
        missing.append("missing_detection_data")
    if not sources.streaming:
        missing.append("missing_streaming_data")
    if not sources.distributed:
        missing.append("missing_distributed_data")
    stale = []
    telemetry_timestamp = str(sources.detection.get("telemetry_timestamp", ""))
    if telemetry_timestamp:
        try:
            observed = datetime.fromisoformat(
                telemetry_timestamp.replace("Z", "+00:00")
            )
            age = (datetime.now(timezone.utc) - observed).total_seconds()
            if age > 900:
                stale.append(f"stale_detection_telemetry:{int(age)}s")
        except ValueError:
            stale.append("invalid_detection_timestamp")
    else:
        stale.append("missing_detection_timestamp")
    visualization_errors = tuple(
        chart.chart_id for chart in visualizations if not chart.points
    )
    latency_ms = float(
        (datetime.now(timezone.utc) - start).total_seconds() * 1000.0
        + len(visualizations)
    )
    return DashboardDiagnostics(
        dashboard_latency_ms=latency_ms,
        visualization_errors=visualization_errors,
        stale_telemetry_warnings=tuple(stale),
        missing_data_warnings=tuple(missing),
    )

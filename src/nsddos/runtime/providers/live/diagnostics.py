"""Live provider diagnostics."""

from __future__ import annotations

from nsddos.runtime.providers.live.contracts import (
    LiveTelemetrySnapshot,
    ProviderDiagnosticRecord,
)


def build_provider_diagnostics(
    snapshot: LiveTelemetrySnapshot,
) -> tuple[ProviderDiagnosticRecord, ...]:
    diagnostics: list[ProviderDiagnosticRecord] = []
    for item in snapshot.provider_health:
        anomalies: list[str] = []
        if item.latency_ms > 500:
            anomalies.append("provider_latency_high")
        if item.state in {"degraded", "reconnecting", "disconnected"}:
            anomalies.append("provider_health_degraded")
        if snapshot.packet_rate < 0 or snapshot.byte_rate < 0:
            anomalies.append("packet_counter_anomaly")
        diagnostics.append(
            ProviderDiagnosticRecord(
                provider=item.provider,
                latency_ms=item.latency_ms,
                health_state=item.state,
                error_count=item.error_count,
                stale="stale" in item.detail,
                anomalies=tuple(anomalies),
            )
        )
    return tuple(diagnostics)

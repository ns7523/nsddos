"""Dashboard engine entrypoint."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from nsddos.dashboard.alerts import build_alerts
from nsddos.dashboard.attacks import build_attack_state
from nsddos.dashboard.contracts import DashboardEvaluation, DashboardSourceBundle
from nsddos.dashboard.diagnostics import build_dashboard_diagnostics
from nsddos.dashboard.history import persist_dashboard_history
from nsddos.dashboard.metrics import build_metrics_state
from nsddos.dashboard.ml_metrics import build_ml_metrics_state
from nsddos.dashboard.policies import build_policy_analytics
from nsddos.dashboard.reports import build_reports
from nsddos.dashboard.streams import build_stream_state
from nsddos.dashboard.threat_intel import build_threat_intel_state
from nsddos.dashboard.timeline import build_timeline
from nsddos.dashboard.validation import validate_dashboard_evaluation
from nsddos.dashboard.visualization import build_visualizations
from nsddos.deployment import latest_deployment_payload
from nsddos.distributed import latest_distributed_evaluation
from nsddos.runtime.detection import latest_detection_evidence
from nsddos.runtime.mitigation import latest_mitigation_evidence
from nsddos.runtime.ml import latest_ml_evaluation
from nsddos.runtime.policy import latest_history_payload as latest_policy_history_payload
from nsddos.runtime.policy import latest_policy_evaluation
from nsddos.runtime.streaming import latest_streaming_evaluation
from nsddos.runtime.verification.replay import replay_verification_runs


def _dashboard_id(environment: str, timestamp: datetime) -> str:
    digest = hashlib.sha256(f"{environment}:{timestamp.isoformat()}".encode("utf-8")).hexdigest()[:16]
    return f"dashboard:{digest}"


def _load_sources() -> DashboardSourceBundle:
    verification_runs = replay_verification_runs(limit=1)
    latest_run = verification_runs.get("runs", [])
    return DashboardSourceBundle(
        detection=latest_detection_evidence(),
        mitigation=latest_mitigation_evidence(),
        policy=latest_policy_evaluation(),
        policy_history=tuple(item for item in latest_policy_history_payload().get("entries", []) if isinstance(item, dict)),
        ml=latest_ml_evaluation(),
        distributed=latest_distributed_evaluation(),
        deployment=latest_deployment_payload(),
        streaming=latest_streaming_evaluation(),
        verification=tuple(item for item in (latest_run[-1].get("results", []) if latest_run else []) if isinstance(item, dict)),
    )


def _dashboard_health(diagnostics_missing: tuple[str, ...], alerts_count: int) -> str:
    if len(diagnostics_missing) >= 3:
        return "failed"
    if diagnostics_missing or alerts_count:
        return "degraded"
    return "healthy"


def generate_dashboard_state(config: dict[str, Any], environment: str = "ops") -> DashboardEvaluation:
    """Build deterministic dashboard state."""
    _ = config
    timestamp = datetime.now(timezone.utc)
    sources = _load_sources()
    metrics = build_metrics_state(sources)
    streams = build_stream_state(sources)
    attacks = build_attack_state(sources)
    timeline = build_timeline(sources)
    policy_analytics = build_policy_analytics(sources)
    ml_metrics = build_ml_metrics_state(sources)
    threat_intel = build_threat_intel_state(sources)
    alerts = build_alerts(sources, attacks, ml_metrics)
    visualizations = build_visualizations(
        streams,
        attacks,
        policy_analytics,
        ml_metrics,
        int(sources.distributed.get("active_nodes", 0)),
        str(sources.distributed.get("cluster_health", "degraded")),
    )
    diagnostics = build_dashboard_diagnostics(sources, visualizations)
    reports = build_reports(
        attacks,
        alerts,
        policy_analytics,
        ml_metrics,
        diagnostics,
        int(sources.distributed.get("active_nodes", 0)),
    )
    evaluation = DashboardEvaluation(
        dashboard_id=_dashboard_id(environment, timestamp),
        active_attacks=attacks.active_attacks,
        active_alerts=len(alerts),
        stream_throughput=streams.event_throughput,
        cluster_nodes=int(sources.distributed.get("active_nodes", 0)),
        ml_confidence=ml_metrics.ml_confidence,
        mitigation_events=metrics.mitigation_frequency,
        policy_events=policy_analytics.policy_events,
        dashboard_health=_dashboard_health(diagnostics.missing_data_warnings, len(alerts)),
        timestamp=timestamp,
        environment=environment,
        metrics=metrics,
        streams=streams,
        attacks=attacks,
        timeline=timeline,
        alerts=alerts,
        visualizations=visualizations,
        policy_analytics=policy_analytics,
        ml_metrics=ml_metrics,
        threat_intel=threat_intel,
        reports=reports,
        diagnostics=diagnostics,
    )
    errors = validate_dashboard_evaluation(evaluation)
    if errors:
        raise ValueError(f"dashboard evaluation invalid: {','.join(errors)}")
    persist_dashboard_history(evaluation)
    return evaluation


def dashboard_alerts(config: dict[str, Any], environment: str = "ops") -> tuple[dict[str, Any], ...]:
    """Return latest dashboard alerts."""
    return tuple(item.to_dict() for item in generate_dashboard_state(config, environment=environment).alerts)


def dashboard_report(config: dict[str, Any], environment: str = "ops") -> tuple[dict[str, Any], ...]:
    """Return latest dashboard reports."""
    return tuple(item.to_dict() for item in generate_dashboard_state(config, environment=environment).reports)


def dashboard_diagnostics(config: dict[str, Any], environment: str = "ops") -> dict[str, Any]:
    """Return latest dashboard diagnostics."""
    return generate_dashboard_state(config, environment=environment).diagnostics.to_dict()

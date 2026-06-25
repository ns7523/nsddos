"""Cyber-operations UI page builders."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from nsddos.bootstrap.diagnostics_engine import collect_diagnostic_findings
from nsddos.bootstrap.orchestrator import load_startup_session
from nsddos.config import load_config
from nsddos.dashboard import generate_dashboard_state, latest_history_payload
from nsddos.service.diagnostics import collect_service_diagnostics
from nsddos.ui.api_client import UiApiClient
from nsddos.ui.lab_console import LAB_HOSTS, control_manager
from nsddos.ui.models import (
    UiActionControl,
    UiChartModel,
    UiChartPoint,
    UiCommandCta,
    UiEventFeed,
    UiEventFeedEntry,
    UiLabActionButton,
    UiLabActionStatus,
    UiLabConsolePayload,
    UiLabEdge,
    UiLabNode,
    UiLabTelemetryItem,
    UiLabTerminalTab,
    UiMetricCard,
    UiPagePayload,
    UiPageSnapshot,
    UiServiceRow,
    UiStatusBarSnapshot,
    UiStatusField,
    UiStatusTile,
    UiTableColumn,
    UiTableRow,
    UiTableSection,
    UiTopologyEdge,
    UiTopologyMap,
    UiTopologyNode,
)

PRIMARY_PATHS = (
    "/ui",
    "/ui/infrastructure",
    "/ui/detection",
    "/ui/mitigation",
    "/ui/live-traffic",
    "/ui/attack-logs",
    "/ui/doctor",
    "/ui/session",
)

EXPLORER_PATHS = (
    "/ui/verification",
    "/ui/convergence",
    "/ui/graph",
    "/ui/timeline",
    "/ui/evidence",
    "/ui/replay",
    "/ui/sessions",
    "/ui/service",
    "/ui/diagnostics",
    "/ui/drift",
    "/ui/synchronization",
)

ATTACK_ORDER = (
    ("syn_flood", "SYN Flood"),
    ("udp_flood", "UDP Flood"),
    ("icmp_flood", "ICMP Flood"),
    ("http_flood", "HTTP Flood"),
    ("slowloris", "Slowloris"),
)

TOPOLOGY_POSITIONS = {
    "internet": (500, 60),
    "router": (500, 140),
    "floodlight": (310, 245),
    "sflowrt": (690, 245),
    "ovs": (500, 320),
    "h1": (250, 420),
    "h2": (500, 420),
    "h3": (750, 420),
    "detection": (500, 500),
    "mitigation": (500, 560),
}

TOPOLOGY_LABELS = {
    "internet": "INTERNET",
    "router": "ROUTER",
    "floodlight": "FLOODLIGHT",
    "sflowrt": "SFLOWRT",
    "ovs": "OVS SWITCH",
    "h1": "h1",
    "h2": "h2",
    "h3": "h3",
    "detection": "DETECTION",
    "mitigation": "MITIGATION",
}

TOPOLOGY_LINKS = (
    ("internet-router", "internet", "router"),
    ("router-floodlight", "router", "floodlight"),
    ("router-sflowrt", "router", "sflowrt"),
    ("floodlight-ovs", "floodlight", "ovs"),
    ("sflowrt-ovs", "sflowrt", "ovs"),
    ("ovs-h1", "ovs", "h1"),
    ("ovs-h2", "ovs", "h2"),
    ("ovs-h3", "ovs", "h3"),
    ("h1-detection", "h1", "detection"),
    ("detection-mitigation", "detection", "mitigation"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, default: str = "UNKNOWN") -> str:
    if value in (None, ""):
        return default
    return str(value)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt_int(value: Any) -> str:
    return str(int(_safe_float(value, 0.0)))


def _fmt_packets(value: Any) -> str:
    return _fmt_int(round(_safe_float(value, 0.0)))


def _fmt_ratio(value: Any) -> str:
    return f"{_safe_float(value, 0.0):.2f}"


def _fmt_bandwidth(value: Any) -> str:
    number = _safe_float(value, 0.0)
    units = ("B/S", "KB/S", "MB/S", "GB/S")
    index = 0
    while number >= 1024 and index < len(units) - 1:
        number /= 1024
        index += 1
    return f"{number:.1f} {units[index]}"


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_uptime(started_at: str) -> str:
    started = _parse_timestamp(started_at)
    if started is None:
        return "--:--"
    elapsed = max(
        int(
            (
                datetime.now(timezone.utc) - started.astimezone(timezone.utc)
            ).total_seconds()
        ),
        0,
    )
    hours, remainder = divmod(elapsed, 3600)
    minutes, _seconds = divmod(remainder, 60)
    return f"{hours:02d}h {minutes:02d}m"


def _field_state(value: str) -> str:
    normalized = value.upper()
    if normalized in {"ONLINE", "LOW"}:
        return "good"
    if normalized in {"DEGRADED", "MEDIUM", "WARN"}:
        return "warn"
    if normalized in {"OFFLINE", "CRITICAL", "HIGH", "FAIL"}:
        return "bad"
    return "neutral"


def _table(
    title: str,
    columns: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    empty_message: str = "NO DATA",
) -> UiTableSection:
    return UiTableSection(
        title=title,
        columns=tuple(
            UiTableColumn(key=f"c{index}", label=label)
            for index, label in enumerate(columns)
        ),
        rows=tuple(UiTableRow(values=row) for row in rows),
        empty_message=empty_message,
    )


def _bundle_table(
    title: str, rows: tuple[tuple[str, str], ...], empty_message: str = "NO DATA"
) -> UiTableSection:
    return _table(title, ("FIELD", "VALUE"), rows, empty_message)


def _event_entry(
    timestamp: str, severity: str, detail: str, source: str
) -> UiEventFeedEntry:
    parsed = _parse_timestamp(timestamp)
    stamp = (
        parsed.astimezone(timezone.utc).strftime("%H:%M:%S")
        if parsed is not None
        else timestamp
    )
    return UiEventFeedEntry(
        timestamp=stamp,
        level=_safe_text(severity, "INFO").upper(),
        message=_safe_text(detail, "event"),
        source=_safe_text(source, "runtime").upper(),
    )


def _pair_points(
    items: list[list[Any]] | tuple[tuple[Any, Any], ...], *, upper: bool = False
) -> tuple[UiChartPoint, ...]:
    points: list[UiChartPoint] = []
    for item in list(items):
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        label = (
            str(item[0]).replace("_", " ").upper()
            if upper
            else str(item[0]).replace("_", " ").title()
        )
        points.append(UiChartPoint(label=label, value=_safe_float(item[1], 0.0)))
    return tuple(points)


def _build_attack_chart(dashboard: dict[str, Any]) -> UiChartModel:
    counts = {
        str(name): _safe_float(value, 0.0)
        for name, value in dashboard.get("attacks", {}).get("attack_types", [])
    }
    return UiChartModel(
        chart_id="attack-distribution",
        title="ATTACK DISTRIBUTION",
        chart_type="bar",
        unit="EVENTS",
        points=tuple(
            UiChartPoint(label=label, value=counts.get(key, 0.0))
            for key, label in ATTACK_ORDER
        ),
    )


def _build_traffic_chart(
    dashboard: dict[str, Any], live: dict[str, Any], title: str = "LIVE PACKETS / SEC"
) -> UiChartModel:
    visualizations = dashboard.get("visualizations", [])
    points = (
        _pair_points(visualizations[0].get("points", []), upper=True)
        if visualizations
        else ()
    )
    if not points:
        base = _safe_float(
            dashboard.get("metrics", {}).get(
                "packet_throughput", live.get("packet_rate", 0.0)
            ),
            0.0,
        )
        points = (
            UiChartPoint("T-4", max(base * 0.62, 0.0)),
            UiChartPoint("T-3", max(base * 0.71, 0.0)),
            UiChartPoint("T-2", max(base * 0.86, 0.0)),
            UiChartPoint("T-1", max(base * 0.93, 0.0)),
            UiChartPoint("NOW", base),
        )
    return UiChartModel(
        chart_id="packets-line",
        title=title,
        chart_type="line",
        unit="PPS",
        points=points,
    )


def _merged_feed(
    history: dict[str, Any], *, limit: int | None = None
) -> tuple[UiEventFeedEntry, ...]:
    items: list[tuple[str, str, str, str]] = []
    for source_key, source_name in (
        ("attack_history", "detection"),
        ("mitigation_history", "mitigation"),
        ("cluster_history", "runtime"),
    ):
        for item in history.get(source_key, []):
            items.append(
                (
                    _safe_text(item.get("timestamp", ""), ""),
                    _safe_text(item.get("severity", item.get("level", "info")), "info"),
                    _safe_text(
                        item.get(
                            "detail",
                            item.get("message", item.get("event_type", "event")),
                        ),
                        "event",
                    ),
                    source_name,
                )
            )
    items.sort(key=lambda item: item[0], reverse=True)
    if limit is not None:
        items = items[:limit]
    return tuple(
        _event_entry(timestamp, severity, detail, source)
        for timestamp, severity, detail, source in items
    )


def _system_status(checks: dict[str, Any]) -> str:
    docker_ok = bool(checks.get("docker_daemon") or checks.get("docker"))
    floodlight_ok = bool(checks.get("floodlight"))
    sflowrt_ok = bool(checks.get("sflowrt"))
    containers_ok = bool(
        checks.get("containers", docker_ok and floodlight_ok and sflowrt_ok)
    )
    if docker_ok and containers_ok and floodlight_ok and sflowrt_ok:
        return "ONLINE"
    if docker_ok or floodlight_ok or sflowrt_ok:
        return "DEGRADED"
    return "OFFLINE"


def _status_bar(bundle: dict[str, Any]) -> UiStatusBarSnapshot:
    dashboard = bundle["dashboard"]
    detection = bundle["detection"]
    live = bundle["live"]
    checks = bundle["health"].get("checks", {})
    startup = bundle["startup_session"]
    system = _system_status(checks)
    return UiStatusBarSnapshot(
        fields=(
            UiStatusField("SYSTEM", system, _field_state(system)),
            UiStatusField(
                "THREAT LEVEL",
                _safe_text(detection.get("risk_level", "LOW")).upper(),
                _field_state(_safe_text(detection.get("risk_level", "LOW")).upper()),
            ),
            UiStatusField(
                "UPTIME",
                _format_uptime(startup.started_at) if startup is not None else "--:--",
            ),
            UiStatusField(
                "PACKETS/S",
                _fmt_packets(
                    dashboard.get("metrics", {}).get(
                        "packet_throughput", live.get("packet_rate", 0.0)
                    )
                ),
            ),
            UiStatusField(
                "ACTIVE ATTACKS",
                _fmt_int(dashboard.get("active_attacks", 0)),
                (
                    "bad"
                    if int(_safe_float(dashboard.get("active_attacks", 0), 0.0))
                    else "good"
                ),
            ),
        ),
        live_state="live",
    )


def _service_rows(bundle: dict[str, Any]) -> tuple[UiServiceRow, ...]:
    checks = bundle["health"].get("checks", {})
    detection = bundle["detection"]
    mitigation = bundle["mitigation"]
    services = (
        ("FLOODLIGHT", checks.get("floodlight"), "CONTROLLER"),
        ("SFLOWRT", checks.get("sflowrt"), "TELEMETRY"),
        ("MININET", checks.get("mininet"), "LAB"),
        ("OVS", checks.get("ovs"), "SWITCH"),
        (
            "DETECTOR",
            detection.get("attack_type") is not None,
            _safe_text(detection.get("attack_type", "ready")).upper(),
        ),
        (
            "MITIGATION",
            mitigation.get("execution_result") is not None,
            _safe_text(mitigation.get("execution_result", "idle")).upper(),
        ),
        ("DOCKER", checks.get("docker_daemon") or checks.get("docker"), "ENGINE"),
    )
    return tuple(
        UiServiceRow(
            name=name, status="ONLINE" if bool(okish) else "OFFLINE", detail=detail
        )
        for name, okish, detail in services
    )


def _status_tiles(bundle: dict[str, Any]) -> tuple[UiStatusTile, ...]:
    detection = bundle["detection"]
    mitigation = bundle["mitigation"]
    live = bundle["live"]
    dashboard = bundle["dashboard"]
    topology_state = (
        "ONLINE" if bundle["health"].get("checks", {}).get("mininet") else "DEGRADED"
    )
    attack_state = (
        "ACTIVE"
        if int(_safe_float(dashboard.get("active_attacks", 0), 0.0))
        else "QUIET"
    )
    mitigation_state = "ENGAGED" if mitigation.get("mitigation_required") else "MONITOR"
    return (
        UiStatusTile(
            "SYSTEM STATE",
            _system_status(bundle["health"].get("checks", {})),
            _field_state(_system_status(bundle["health"].get("checks", {}))),
            "container stack posture",
        ),
        UiStatusTile(
            "THREAT LEVEL",
            _safe_text(detection.get("risk_level", "LOW")).upper(),
            _field_state(_safe_text(detection.get("risk_level", "LOW")).upper()),
            "live classifier severity",
        ),
        UiStatusTile(
            "ATTACK STATUS",
            attack_state,
            "bad" if attack_state == "ACTIVE" else "good",
            _safe_text(detection.get("attack_type", "normal"))
            .replace("_", " ")
            .upper(),
        ),
        UiStatusTile(
            "TOPOLOGY",
            topology_state,
            _field_state(topology_state),
            "fabric + service graph",
        ),
        UiStatusTile(
            "MITIGATION",
            mitigation_state,
            "warn" if mitigation_state == "ENGAGED" else "neutral",
            _safe_text(mitigation.get("execution_result", "standby")).upper(),
        ),
        UiStatusTile(
            "STREAM",
            _safe_text(live.get("provider_source", "unknown")).upper(),
            "good",
            f"{_fmt_packets(live.get('packet_rate', 0.0))} pps",
        ),
    )


def _metric_cards(bundle: dict[str, Any]) -> tuple[UiMetricCard, ...]:
    dashboard = bundle["dashboard"]
    live = bundle["live"]
    ml = bundle["ml"]
    detection = bundle["detection"]
    return (
        UiMetricCard(
            "PACKETS / SEC",
            _fmt_packets(
                live.get(
                    "packet_rate",
                    dashboard.get("metrics", {}).get("packet_throughput", 0.0),
                )
            ),
            "live ingress rate",
            "good",
        ),
        UiMetricCard(
            "BANDWIDTH",
            _fmt_bandwidth(
                live.get(
                    "byte_rate",
                    dashboard.get("metrics", {}).get("byte_throughput", 0.0),
                )
            ),
            "telemetry throughput",
            "good",
        ),
        UiMetricCard(
            "FLOWS / SEC",
            _fmt_int(live.get("active_flows", 0)),
            "active flow count",
            "neutral",
        ),
        UiMetricCard(
            "ANOMALY SCORE",
            _fmt_ratio(ml.get("anomaly_score", 0.0)),
            "ml anomaly channel",
            "warn" if _safe_float(ml.get("anomaly_score", 0.0)) >= 0.5 else "good",
        ),
        UiMetricCard(
            "CONFIDENCE",
            _fmt_ratio(detection.get("confidence", 0.0)),
            _safe_text(detection.get("attack_type", "normal"))
            .replace("_", " ")
            .upper(),
            "bad" if bool(dashboard.get("active_attacks", 0)) else "good",
        ),
        UiMetricCard(
            "ATTACK RATE",
            _fmt_int(dashboard.get("active_attacks", 0)),
            "active attack sessions",
            (
                "bad"
                if int(_safe_float(dashboard.get("active_attacks", 0), 0.0))
                else "good"
            ),
        ),
    )


def _attack_controls() -> tuple[UiActionControl, ...]:
    return (
        UiActionControl(
            "Launch SYN Flood",
            "run-syn-flood",
            "attack",
            "tcp flood against live lab target",
        ),
        UiActionControl(
            "Launch UDP Flood", "run-udp-flood", "attack", "udp saturation attack"
        ),
        UiActionControl(
            "Launch ICMP Flood",
            "run-icmp-flood",
            "attack",
            "icmp flood via existing runtime helper",
        ),
        UiActionControl(
            "Stop Attack", "stop-attack", "control", "halt active live attack suite"
        ),
    )


def _topology(bundle: dict[str, Any]) -> UiTopologyMap:
    checks = bundle["health"].get("checks", {})
    service_states = {
        "internet": "ONLINE",
        "router": (
            "ONLINE"
            if (checks.get("docker_daemon") or checks.get("docker"))
            else "OFFLINE"
        ),
        "floodlight": "ONLINE" if checks.get("floodlight") else "OFFLINE",
        "sflowrt": "ONLINE" if checks.get("sflowrt") else "OFFLINE",
        "ovs": "ONLINE" if checks.get("ovs") else "OFFLINE",
        "h1": "ONLINE" if checks.get("mininet") else "DEGRADED",
        "h2": "ONLINE" if checks.get("mininet") else "DEGRADED",
        "h3": "ONLINE" if checks.get("mininet") else "DEGRADED",
        "detection": (
            "ONLINE"
            if bundle["detection"].get("attack_type") is not None
            else "OFFLINE"
        ),
        "mitigation": (
            "ONLINE"
            if bundle["mitigation"].get("execution_result") is not None
            else "DEGRADED"
        ),
    }
    nodes = tuple(
        UiTopologyNode(
            node_id=node_id,
            label=TOPOLOGY_LABELS[node_id],
            x=TOPOLOGY_POSITIONS[node_id][0],
            y=TOPOLOGY_POSITIONS[node_id][1],
            state=service_states[node_id],
        )
        for node_id in TOPOLOGY_LABELS
    )
    node_state = {node.node_id: node.state for node in nodes}
    edges = tuple(
        UiTopologyEdge(
            edge_id=edge_id,
            source=source,
            target=target,
            state=(
                "ONLINE"
                if node_state[source] == "ONLINE" and node_state[target] == "ONLINE"
                else (
                    "OFFLINE"
                    if "OFFLINE" in {node_state[source], node_state[target]}
                    else "DEGRADED"
                )
            ),
            pulse=node_state[source] == "ONLINE" and node_state[target] == "ONLINE",
        )
        for edge_id, source, target in TOPOLOGY_LINKS
    )
    return UiTopologyMap(title="NETWORK TOPOLOGY", nodes=nodes, edges=edges)


class UiPageBuilder:
    """Build SSR page payloads from existing read-only sources."""

    def __init__(self, client: UiApiClient | None = None) -> None:
        self.client = client or UiApiClient()

    def _api(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.client.get(path, params=params)

    def _bundle(self) -> dict[str, Any]:
        config = load_config()
        return {
            "dashboard": generate_dashboard_state(config).to_dict(),
            "history": latest_history_payload(),
            "detection": self._api("/runtime/detection")["payload"],
            "mitigation": self._api("/runtime/mitigation")["payload"],
            "ml": self._api("/runtime/ml/infer")["payload"],
            "live": self._api("/runtime/live-telemetry")["payload"],
            "health": self._api("/health")["payload"],
            "provider_health": self._api(
                "/runtime/provider-health", {"limit": 25, "offset": 0}
            )["payload"],
            "service": self._api("/runtime/service", {"limit": 25, "offset": 0})[
                "payload"
            ],
            "reports": self._api("/dashboard/report")["payload"],
            "diagnostics": self._api("/dashboard/diagnostics")["payload"],
            "service_diagnostics": collect_service_diagnostics(),
            "startup_session": load_startup_session(),
        }

    def overview(self) -> UiPagePayload:
        bundle = self._bundle()
        return UiPagePayload(
            name="overview",
            title="OVERVIEW",
            eyebrow="MISSION CONTROL",
            description="SYSTEM STATE / THREAT LEVEL / SERVICE MATRIX / LIVE TOPOLOGY",
            active_path="/ui",
            status_bar=_status_bar(bundle),
            stats=_metric_cards(bundle),
            statuses=_status_tiles(bundle),
            traffic_chart=_build_traffic_chart(bundle["dashboard"], bundle["live"]),
            attack_chart=_build_attack_chart(bundle["dashboard"]),
            topology=_topology(bundle),
            feed=UiEventFeed(
                title="LIVE EVENT FEED",
                entries=_merged_feed(bundle["history"], limit=5),
                preview=True,
            ),
            services=_service_rows(bundle),
            tables=(
                _bundle_table(
                    "RUNTIME",
                    (
                        (
                            "BANDWIDTH",
                            _fmt_bandwidth(
                                bundle["dashboard"]
                                .get("metrics", {})
                                .get(
                                    "byte_throughput",
                                    bundle["live"].get("byte_rate", 0.0),
                                )
                            ),
                        ),
                        (
                            "ACTIVE FLOWS",
                            _fmt_int(bundle["live"].get("active_flows", 0)),
                        ),
                        (
                            "SESSIONS",
                            _fmt_int(
                                len(
                                    bundle["service_diagnostics"].get(
                                        "active_sessions", []
                                    )
                                )
                            ),
                        ),
                        (
                            "UPDATED",
                            _safe_text(
                                bundle["live"].get(
                                    "timestamp",
                                    bundle["dashboard"].get("timestamp", _now_iso()),
                                )
                            ),
                        ),
                    ),
                ),
            ),
            updated_at=_safe_text(
                bundle["live"].get(
                    "timestamp", bundle["dashboard"].get("timestamp", _now_iso())
                )
            ),
        )

    def infrastructure(self) -> UiPagePayload:
        bundle = self._bundle()
        provider_rows = tuple(
            (
                _safe_text(
                    item.get("provider_name", item.get("id", "provider"))
                ).upper(),
                _safe_text(
                    item.get("health_state", item.get("state", "unknown"))
                ).upper(),
                _safe_text(
                    item.get("detail", item.get("controller_status", "")), "UNKNOWN"
                ).upper(),
            )
            for item in bundle["provider_health"].get("items", [])
        )
        return UiPagePayload(
            name="infrastructure",
            title="LIVE TOPOLOGY",
            eyebrow="FABRIC VIEW",
            description="LIVE LINK GRAPH / CONTAINER SERVICES / PROVIDER STATE",
            active_path="/ui/infrastructure",
            status_bar=_status_bar(bundle),
            stats=_metric_cards(bundle)[:3],
            statuses=_status_tiles(bundle)[:4],
            topology=_topology(bundle),
            services=_service_rows(bundle),
            tables=(
                _table(
                    "PROVIDER HEALTH", ("SERVICE", "STATE", "DETAIL"), provider_rows
                ),
                _bundle_table(
                    "HOST CHECKS",
                    (
                        (
                            "DOCKER",
                            (
                                "ONLINE"
                                if bundle["health"]
                                .get("checks", {})
                                .get("docker_daemon")
                                else "OFFLINE"
                            ),
                        ),
                        (
                            "SESSION",
                            (
                                "PRESENT"
                                if bundle["startup_session"] is not None
                                else "MISSING"
                            ),
                        ),
                    ),
                ),
            ),
            updated_at=_now_iso(),
        )

    def detection(self) -> UiPagePayload:
        bundle = self._bundle()
        ml = bundle["ml"]
        detection = bundle["detection"]
        return UiPagePayload(
            name="detection",
            title="DETECTION ENGINE",
            eyebrow="ML / ANALYTICS",
            description="ACTIVE MODEL / ANOMALY SCORE / CONFIDENCE / FEATURE VECTOR / LATENCY",
            active_path="/ui/detection",
            status_bar=_status_bar(bundle),
            stats=(
                UiMetricCard(
                    "ACTIVE MODEL",
                    _safe_text(ml.get("predicted_attack_type", "normal"))
                    .replace("_", " ")
                    .upper(),
                    "current ml verdict",
                    "neutral",
                ),
                UiMetricCard(
                    "ANOMALY SCORE",
                    _fmt_ratio(ml.get("anomaly_score", 0.0)),
                    "feature anomaly signal",
                    "warn",
                ),
                UiMetricCard(
                    "CONFIDENCE",
                    _fmt_ratio(ml.get("confidence_score", ml.get("confidence", 0.0))),
                    "model confidence",
                    "good",
                ),
                UiMetricCard(
                    "LATENCY",
                    f"{_fmt_ratio(bundle['diagnostics'].get('diagnostics', {}).get('dashboard_latency_ms', 0.0))} ms",
                    "dashboard inference latency",
                    "neutral",
                ),
            ),
            statuses=_status_tiles(bundle)[:4],
            attack_chart=_build_attack_chart(bundle["dashboard"]),
            charts=(
                UiChartModel(
                    chart_id="detection-scores",
                    title="DETECTION SCORES",
                    chart_type="bar",
                    unit="SCORE",
                    points=(
                        UiChartPoint(
                            "CONFIDENCE", _safe_float(detection.get("confidence", 0.0))
                        ),
                        UiChartPoint(
                            "ML CLASS", _safe_float(ml.get("confidence_score", 0.0))
                        ),
                        UiChartPoint(
                            "ANOMALY", _safe_float(ml.get("anomaly_score", 0.0))
                        ),
                        UiChartPoint("DRIFT", _safe_float(ml.get("drift_score", 0.0))),
                    ),
                ),
            ),
            tables=(
                _bundle_table(
                    "DETECTION STATE",
                    (
                        (
                            "ATTACK TYPE",
                            _safe_text(detection.get("attack_type", "normal")).upper(),
                        ),
                        (
                            "RISK LEVEL",
                            _safe_text(detection.get("risk_level", "low")).upper(),
                        ),
                        (
                            "PREDICTED",
                            _safe_text(
                                ml.get("predicted_attack_type", "normal")
                            ).upper(),
                        ),
                        ("ANOMALY", _fmt_ratio(ml.get("anomaly_score", 0.0))),
                        (
                            "FEATURE VECTOR",
                            f"SYN={_fmt_ratio(ml.get('syn_rate', 0.0))} UDP={_fmt_ratio(ml.get('udp_rate', 0.0))} ICMP={_fmt_ratio(ml.get('icmp_rate', 0.0))}",
                        ),
                        (
                            "LATENCY",
                            f"{_fmt_ratio(bundle['diagnostics'].get('diagnostics', {}).get('dashboard_latency_ms', 0.0))} ms",
                        ),
                    ),
                ),
            ),
            feed=UiEventFeed(
                title="DETECTION EVENTS",
                entries=_merged_feed(bundle["history"], limit=8),
            ),
            updated_at=_safe_text(bundle["live"].get("timestamp", _now_iso())),
        )

    def mitigation(self) -> UiPagePayload:
        bundle = self._bundle()
        mitigation = bundle["mitigation"]
        blocked = list(bundle["dashboard"].get("attacks", {}).get("source_ips", []))
        if mitigation.get("target_ip"):
            blocked.insert(0, [mitigation.get("target_ip"), 1.0])
        timeline = tuple(
            (entry.timestamp, entry.level, entry.message)
            for entry in _merged_feed(
                {"mitigation_history": bundle["history"].get("mitigation_history", [])},
                limit=12,
            )
        )
        return UiPagePayload(
            name="mitigation",
            title="MITIGATION PANEL",
            eyebrow="POLICY ENFORCEMENT",
            description="BLOCKED FLOWS / MITIGATION ACTIONS / RULE INSERTION / ACTIVE PROTECTIONS",
            active_path="/ui/mitigation",
            status_bar=_status_bar(bundle),
            stats=(
                UiMetricCard(
                    "BLOCKED FLOWS",
                    _fmt_int(len(blocked)),
                    "tracked blocked flow sources",
                    "bad" if blocked else "good",
                ),
                UiMetricCard(
                    "ACTION",
                    _safe_text(mitigation.get("mitigation_action", "alert_only"))
                    .replace("_", " ")
                    .upper(),
                    "current active policy",
                    "warn",
                ),
                UiMetricCard(
                    "TARGET",
                    _safe_text(mitigation.get("target_ip", "none")).upper(),
                    "current mitigated target",
                    "neutral",
                ),
                UiMetricCard(
                    "PROTECTIONS",
                    "ACTIVE" if mitigation.get("mitigation_required") else "MONITOR",
                    "protection posture",
                    "warn" if mitigation.get("mitigation_required") else "good",
                ),
            ),
            statuses=_status_tiles(bundle)[:5],
            charts=(
                UiChartModel(
                    chart_id="blocked-ips",
                    title="BLOCKED IPS",
                    chart_type="bar",
                    unit="COUNT",
                    points=_pair_points(blocked, upper=True),
                ),
            ),
            tables=(
                _bundle_table(
                    "ACTIVE MITIGATION",
                    (
                        (
                            "REQUIRED",
                            "YES" if mitigation.get("mitigation_required") else "NO",
                        ),
                        (
                            "ACTION",
                            _safe_text(
                                mitigation.get("mitigation_action", "alert_only")
                            )
                            .replace("_", " ")
                            .upper(),
                        ),
                        (
                            "TARGET",
                            _safe_text(mitigation.get("target_ip", "none")).upper(),
                        ),
                        (
                            "RESULT",
                            _safe_text(
                                mitigation.get("execution_result", "pending")
                            ).upper(),
                        ),
                        ("FLOW RULES", _fmt_int(len(blocked))),
                        (
                            "PROTECTIONS",
                            (
                                "ACTIVE"
                                if mitigation.get("mitigation_required")
                                else "MONITOR"
                            ),
                        ),
                    ),
                ),
                _table(
                    "POLICY TIMELINE",
                    ("TIME", "LEVEL", "DETAIL"),
                    timeline,
                    "NO MITIGATION EVENTS",
                ),
            ),
            feed=UiEventFeed(
                title="MITIGATION FEED",
                entries=_merged_feed(bundle["history"], limit=10),
            ),
            updated_at=_safe_text(bundle["live"].get("timestamp", _now_iso())),
        )

    def live_traffic(self) -> UiPagePayload:
        bundle = self._bundle()
        dashboard = bundle["dashboard"]
        return UiPagePayload(
            name="live-traffic",
            title="LIVE TRAFFIC PANEL",
            eyebrow="TELEMETRY",
            description="PACKETS / SEC / BANDWIDTH / FLOWS / PACKET DROPS / ATTACK RATE",
            active_path="/ui/live-traffic",
            status_bar=_status_bar(bundle),
            stats=(
                UiMetricCard(
                    "PACKETS / SEC",
                    _fmt_packets(bundle["live"].get("packet_rate", 0.0)),
                    "current ingress rate",
                    "good",
                ),
                UiMetricCard(
                    "BANDWIDTH",
                    _fmt_bandwidth(bundle["live"].get("byte_rate", 0.0)),
                    "current bandwidth",
                    "good",
                ),
                UiMetricCard(
                    "FLOWS / SEC",
                    _fmt_int(bundle["live"].get("active_flows", 0)),
                    "active flows",
                    "neutral",
                ),
                UiMetricCard(
                    "PACKET DROPS",
                    _fmt_int(
                        max(
                            int(_safe_float(dashboard.get("active_alerts", 0), 0.0))
                            - int(_safe_float(dashboard.get("active_attacks", 0), 0.0)),
                            0,
                        )
                    ),
                    "derived drop proxy",
                    "warn",
                ),
                UiMetricCard(
                    "ATTACK RATE",
                    _fmt_int(dashboard.get("active_attacks", 0)),
                    "concurrent attacks",
                    (
                        "bad"
                        if int(_safe_float(dashboard.get("active_attacks", 0), 0.0))
                        else "good"
                    ),
                ),
            ),
            statuses=_status_tiles(bundle)[:4],
            traffic_chart=_build_traffic_chart(
                dashboard, bundle["live"], title="PACKETS / SEC"
            ),
            charts=(
                UiChartModel(
                    chart_id="source-ip",
                    title="SOURCE IP DISTRIBUTION",
                    chart_type="bar",
                    unit="COUNT",
                    points=_pair_points(
                        dashboard.get("attacks", {}).get("source_ips", []), upper=True
                    ),
                ),
                UiChartModel(
                    chart_id="protocol-distribution",
                    title="PROTOCOL DISTRIBUTION",
                    chart_type="bar",
                    unit="RATIO",
                    points=_pair_points(
                        dashboard.get("threat_intel", {}).get(
                            "suspicious_protocol_concentration", []
                        ),
                        upper=True,
                    ),
                ),
            ),
            tables=(
                _bundle_table(
                    "TELEMETRY",
                    (
                        (
                            "PACKET RATE",
                            _fmt_packets(bundle["live"].get("packet_rate", 0.0)),
                        ),
                        (
                            "BYTE RATE",
                            _fmt_bandwidth(bundle["live"].get("byte_rate", 0.0)),
                        ),
                        (
                            "ACTIVE FLOWS",
                            _fmt_int(bundle["live"].get("active_flows", 0)),
                        ),
                        (
                            "PROVIDER",
                            _safe_text(
                                bundle["live"].get("provider_source", "unknown")
                            ).upper(),
                        ),
                        ("ATTACK RATE", _fmt_int(dashboard.get("active_attacks", 0))),
                    ),
                ),
            ),
            feed=UiEventFeed(
                title="TRAFFIC FEED", entries=_merged_feed(bundle["history"], limit=10)
            ),
            updated_at=_safe_text(bundle["live"].get("timestamp", _now_iso())),
        )

    def attack_logs(self) -> UiPagePayload:
        bundle = self._bundle()
        entries = _merged_feed(bundle["history"])
        action_status = control_manager.latest_status()
        attack_source = (
            bundle["dashboard"].get("attacks", {}).get("source_ips", [["10.0.0.4", 1]])
        )
        timeline_points = tuple(
            UiChartPoint(entry.timestamp, float(index + 1))
            for index, entry in enumerate(reversed(entries[-8:]))
        )
        return UiPagePayload(
            name="attack-logs",
            title="ATTACK SIMULATOR",
            eyebrow="OFFENSIVE LAB",
            description="SYN / UDP / ICMP TRIGGERING WITH LIVE PROGRESS AND TIMELINE",
            active_path="/ui/attack-logs",
            status_bar=_status_bar(bundle),
            stats=(
                UiMetricCard(
                    "ACTIVE ACTION",
                    _safe_text(action_status.get("action", "idle"))
                    .replace("-", " ")
                    .upper(),
                    "latest operator command",
                    "warn",
                ),
                UiMetricCard(
                    "ACTION STATE",
                    _safe_text(action_status.get("state", "ready")).upper(),
                    "live simulator status",
                    "good",
                ),
                UiMetricCard(
                    "SOURCE",
                    _safe_text(attack_source[0][0], "10.0.0.4").upper(),
                    "simulated source",
                    "neutral",
                ),
                UiMetricCard(
                    "TARGET",
                    _safe_text(
                        bundle["mitigation"].get("target_ip", "10.0.0.2")
                    ).upper(),
                    "current target",
                    "neutral",
                ),
            ),
            statuses=_status_tiles(bundle)[:4],
            actions=_attack_controls(),
            attack_chart=UiChartModel(
                chart_id="attack-timeline",
                title="ATTACK TIMELINE",
                chart_type="line",
                unit="EVENTS",
                points=timeline_points or (UiChartPoint("NOW", 0.0),),
            ),
            feed=UiEventFeed(title="ATTACK LOG", entries=entries),
            tables=(
                _bundle_table(
                    "SIMULATOR STATUS",
                    (
                        (
                            "ACTION",
                            _safe_text(action_status.get("action", "idle")).upper(),
                        ),
                        (
                            "STATE",
                            _safe_text(action_status.get("state", "ready")).upper(),
                        ),
                        (
                            "DETAIL",
                            _safe_text(
                                action_status.get(
                                    "detail", "Awaiting operator command."
                                )
                            ).upper(),
                        ),
                        ("SOURCE", _safe_text(attack_source[0][0], "10.0.0.4").upper()),
                        (
                            "TARGET",
                            _safe_text(
                                bundle["mitigation"].get("target_ip", "10.0.0.2")
                            ).upper(),
                        ),
                    ),
                ),
            ),
            updated_at=_safe_text(bundle["live"].get("timestamp", _now_iso())),
        )

    def lab_console(self) -> UiPagePayload:
        bundle = self._bundle()
        checks = bundle["health"].get("checks", {})
        detection = bundle["detection"]
        mitigation = bundle["mitigation"]
        live = bundle["live"]
        return UiPagePayload(
            name="lab-console",
            title="LAB CONSOLE",
            eyebrow="TERMINAL ACCESS",
            description="LIVE HOST SHELLS / TELEMETRY / ATTACK CONTROLS",
            active_path="/ui/lab-console",
            status_bar=_status_bar(bundle),
            lab_console=UiLabConsolePayload(
                nodes=tuple(
                    UiLabNode(
                        node_id=host,
                        label=host,
                        kind="host",
                        state="online" if checks.get("mininet") else "degraded",
                        detail=f"10.0.0.{index + 1}",
                        metadata={"host": host},
                        actions=("open_shell",),
                    )
                    for index, host in enumerate(LAB_HOSTS)
                )
                + (
                    UiLabNode(
                        node_id="detector",
                        label="Detector",
                        kind="service",
                        state="online" if detection.get("attack_type") else "offline",
                        detail=_safe_text(
                            detection.get("attack_type", "normal")
                        ).upper(),
                        metadata={
                            "risk": _safe_text(
                                detection.get("risk_level", "low")
                            ).upper()
                        },
                        actions=("inspect",),
                    ),
                    UiLabNode(
                        node_id="mitigation",
                        label="Mitigation engine",
                        kind="service",
                        state=(
                            "active"
                            if mitigation.get("mitigation_required")
                            else "planned"
                        ),
                        detail=_safe_text(
                            mitigation.get("mitigation_action", "alert_only")
                        )
                        .replace("_", " ")
                        .upper(),
                        metadata={
                            "result": _safe_text(
                                mitigation.get("execution_result", "planned")
                            ).upper()
                        },
                        actions=("inspect",),
                    ),
                ),
                edges=(
                    UiLabEdge(source="h1", target="detector", label="telemetry"),
                    UiLabEdge(source="h2", target="detector", label="telemetry"),
                    UiLabEdge(source="h3", target="detector", label="telemetry"),
                    UiLabEdge(source="detector", target="mitigation", label="decision"),
                ),
                telemetry=(
                    UiLabTelemetryItem(
                        "Packets/sec",
                        _fmt_packets(live.get("packet_rate", 0.0)),
                        "Live packet rate",
                        "good",
                    ),
                    UiLabTelemetryItem(
                        "Mitigation state",
                        _safe_text(
                            mitigation.get("execution_result", "planned")
                        ).upper(),
                        "Latest mitigation state",
                        "warn",
                    ),
                ),
                terminal_tabs=tuple(
                    UiLabTerminalTab(
                        host=host,
                        label=host,
                        state="connected" if checks.get("mininet") else "offline",
                        prompt=f"{host}#",
                    )
                    for host in LAB_HOSTS
                ),
                action_buttons=(
                    UiLabActionButton("Open h1 shell", "open-h1-shell", "shell"),
                    UiLabActionButton("Run SYN Flood", "run-syn-flood", "attack"),
                    UiLabActionButton("Run UDP Flood", "run-udp-flood", "attack"),
                    UiLabActionButton("Run ICMP Flood", "run-icmp-flood", "attack"),
                    UiLabActionButton("Stop attack", "stop-attack", "control"),
                ),
                action_status=UiLabActionStatus(
                    action=str(control_manager.latest_status().get("action", "idle")),
                    state=str(control_manager.latest_status().get("state", "ready")),
                    detail=str(
                        control_manager.latest_status().get(
                            "detail", "Awaiting operator command."
                        )
                    ),
                    timestamp=str(
                        control_manager.latest_status().get("timestamp", _now_iso())
                    ),
                ),
            ),
            updated_at=_safe_text(live.get("timestamp", _now_iso())),
        )

    def doctor(self) -> UiPagePayload:
        bundle = self._bundle()
        findings = tuple(
            item for item in collect_diagnostic_findings() if item.status == "fail"
        )
        rows = tuple(
            (item.area.upper(), item.check_name.upper(), item.detail.upper())
            for item in findings
        )
        return UiPagePayload(
            name="doctor",
            title="DOCTOR PANEL",
            eyebrow="DIAGNOSTICS",
            description="FAILED CHECKS / RUNTIME DIAGNOSTICS / REPAIR GUIDANCE",
            active_path="/ui/doctor",
            status_bar=_status_bar(bundle),
            statuses=_status_tiles(bundle)[:4],
            tables=(
                _table(
                    "FAILED SUBSYSTEMS",
                    ("AREA", "CHECK", "DETAIL"),
                    rows,
                    "NO FAILED SUBSYSTEMS",
                ),
            ),
            cta=UiCommandCta(
                title="CLI REPAIR",
                command="nsddos doctor",
                detail="WEB UI IS READ ONLY. RUN REPAIR FROM CLI.",
            ),
            updated_at=_now_iso(),
        )

    def session(self) -> UiPagePayload:
        bundle = self._bundle()
        startup = bundle["startup_session"]
        diagnostics = bundle["service_diagnostics"]
        startup_rows = (
            (
                ("STARTED AT", startup.started_at),
                ("HEALTH", startup.health_state.upper()),
                ("UI URL", startup.ui_url),
                ("CONTAINERS", ", ".join(startup.running_containers) or "NONE"),
            )
            if startup is not None
            else ()
        )
        service_rows = tuple(
            (
                _safe_text(item.get("id", "")).upper(),
                _safe_text(item.get("kind", "")).upper(),
                _safe_text(
                    item.get("state", item.get("sync_state", "unknown"))
                ).upper(),
                _safe_text(item.get("owner", "system")).upper(),
            )
            for item in bundle["service"].get("items", [])
        )
        return UiPagePayload(
            name="session",
            title="SESSION PANEL",
            eyebrow="RUNTIME METADATA",
            description="CURRENT SESSION / RUNTIME METADATA / SERVICE STATUS",
            active_path="/ui/session",
            status_bar=_status_bar(bundle),
            stats=(
                UiMetricCard(
                    "ACTIVE SESSIONS",
                    _fmt_int(len(diagnostics.get("active_sessions", []))),
                    "service session count",
                    "good",
                ),
                UiMetricCard(
                    "HEARTBEATS",
                    _fmt_int(diagnostics.get("heartbeat_count", 0)),
                    "runtime heartbeats",
                    "neutral",
                ),
                UiMetricCard(
                    "REPLAY EVENTS",
                    _fmt_int(diagnostics.get("replay", {}).get("event_count", 0)),
                    "replay ledger size",
                    "neutral",
                ),
                UiMetricCard(
                    "SYNC",
                    _safe_text(
                        diagnostics.get("synchronization", {}).get("state", "unknown")
                    ).upper(),
                    "synchronization state",
                    "good",
                ),
            ),
            statuses=_status_tiles(bundle)[:4],
            tables=(
                _bundle_table(
                    "ACTIVE SESSION", startup_rows, "NO STARTUP SESSION RECORDED."
                ),
                _table(
                    "RUNTIME STATE",
                    ("ID", "KIND", "STATE", "OWNER"),
                    service_rows,
                    "NO RUNTIME STATE",
                ),
                _bundle_table(
                    "SERVICE SESSION COUNTS",
                    (
                        (
                            "ACTIVE SESSIONS",
                            _fmt_int(len(diagnostics.get("active_sessions", []))),
                        ),
                        ("HEARTBEATS", _fmt_int(diagnostics.get("heartbeat_count", 0))),
                        (
                            "REPLAY EVENTS",
                            _fmt_int(
                                diagnostics.get("replay", {}).get("event_count", 0)
                            ),
                        ),
                    ),
                ),
            ),
            updated_at=_now_iso(),
        )

    def explorer(
        self,
        path: str,
        title: str,
        payload_path: str,
        description: str,
        params: dict[str, Any] | None = None,
    ) -> UiPagePayload:
        bundle = self._bundle()
        response = self._api(payload_path, params or {"limit": 25, "offset": 0})[
            "payload"
        ]
        rows = tuple(dict(item) for item in response.get("items", []))
        columns = tuple(sorted({key for row in rows for key in row.keys()}))
        table_rows = tuple(
            tuple(_safe_text(row.get(column, ""), "") for column in columns)
            for row in rows
        )
        return UiPagePayload(
            name=path.rsplit("/", 1)[-1] or "overview",
            title=title.upper(),
            description=description.upper(),
            active_path=path,
            status_bar=_status_bar(bundle),
            tables=(
                _table(
                    title.upper(),
                    tuple(column.replace("_", " ").upper() for column in columns),
                    table_rows,
                ),
                _bundle_table(
                    "SUMMARY",
                    (
                        ("TOTAL", _fmt_int(response.get("total", len(rows)))),
                        (
                            "REPLAY SAFE",
                            "YES" if bool(response.get("replay_safe", True)) else "NO",
                        ),
                        (
                            "TIMESTAMP",
                            _safe_text(response.get("timestamp", _now_iso())),
                        ),
                    ),
                ),
            ),
            updated_at=_safe_text(response.get("timestamp", _now_iso())),
        )

    def snapshot_for(self, name: str) -> UiPageSnapshot:
        mapping: dict[str, Callable[[], UiPagePayload]] = {
            "overview": self.overview,
            "infrastructure": self.infrastructure,
            "detection": self.detection,
            "mitigation": self.mitigation,
            "live-traffic": self.live_traffic,
            "lab-console": self.lab_console,
            "attack-logs": self.attack_logs,
            "doctor": self.doctor,
            "session": self.session,
        }
        return UiPageSnapshot(status="ok", page=mapping[name]())

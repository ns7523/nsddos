"""UI typed models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nsddos.runtime.models import SCHEMA_VERSION


@dataclass(frozen=True)
class UiNavItem:
    """Navigation item."""

    label: str
    path: str
    group: str
    icon: str = ""
    active: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiMetricCard:
    """Headline KPI card."""

    label: str
    value: str
    detail: str
    tone: str = "neutral"
    delta: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiStatusTile:
    """Status badge tile."""

    label: str
    value: str
    state: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiStatusField:
    """Status bar field."""

    label: str
    value: str
    state: str = "neutral"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiStatusBarSnapshot:
    """Shared top bar snapshot."""

    fields: tuple[UiStatusField, ...]
    live_state: str = "live"

    def to_dict(self) -> dict[str, Any]:
        return {
            "fields": [field.to_dict() for field in self.fields],
            "live_state": self.live_state,
        }


@dataclass(frozen=True)
class UiChartPoint:
    """Chart datapoint."""

    label: str
    value: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiChartModel:
    """Chart payload."""

    chart_id: str
    title: str
    chart_type: str
    unit: str
    points: tuple[UiChartPoint, ...]
    tone: str = "green"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["points"] = [point.to_dict() for point in self.points]
        return payload


@dataclass(frozen=True)
class UiTimelineEntry:
    """Timeline row."""

    title: str
    detail: str
    timestamp: str
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiEventFeedEntry:
    """Terminal-style feed row."""

    timestamp: str
    level: str
    message: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiEventFeed:
    """Terminal-style event feed."""

    title: str
    entries: tuple[UiEventFeedEntry, ...]
    preview: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "entries": [entry.to_dict() for entry in self.entries],
            "preview": self.preview,
        }


@dataclass(frozen=True)
class UiServiceRow:
    """Service status row."""

    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiTopologyNode:
    """Tracked cyber-ops topology node."""

    node_id: str
    label: str
    x: int
    y: int
    state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiTopologyEdge:
    """Tracked cyber-ops topology edge."""

    edge_id: str
    source: str
    target: str
    state: str
    pulse: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiTopologyMap:
    """Tracked cyber-ops topology map."""

    title: str
    nodes: tuple[UiTopologyNode, ...]
    edges: tuple[UiTopologyEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


@dataclass(frozen=True)
class UiTableColumn:
    """Structured table column."""

    key: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiTableSection:
    """Structured data table."""

    title: str
    columns: tuple[UiTableColumn, ...]
    rows: tuple[Any, ...]
    empty_message: str = "No data."

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "columns": [column.to_dict() for column in self.columns],
            "rows": [row.to_dict() if hasattr(row, "to_dict") else row for row in self.rows],
            "empty_message": self.empty_message,
        }


@dataclass(frozen=True)
class UiTableRow:
    """Tracked table row variant."""

    values: tuple[str, ...]
    state: str = "neutral"

    def to_dict(self) -> dict[str, Any]:
        return {"values": list(self.values), "state": self.state}


@dataclass(frozen=True)
class UiCommandCta:
    """Read-only command CTA."""

    title: str
    command: str
    detail: str
    action_label: str = "Copy Command"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiLabNode:
    """LAB topology node."""

    node_id: str
    label: str
    kind: str
    state: str
    detail: str
    metadata: dict[str, str] = field(default_factory=dict)
    actions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "kind": self.kind,
            "state": self.state,
            "detail": self.detail,
            "metadata": dict(self.metadata),
            "actions": list(self.actions),
        }


@dataclass(frozen=True)
class UiLabEdge:
    """LAB topology edge."""

    source: str
    target: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiLabTelemetryItem:
    """LAB telemetry tile."""

    label: str
    value: str
    detail: str
    state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiLabTerminalTab:
    """LAB terminal tab state."""

    host: str
    label: str
    state: str
    prompt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiLabActionButton:
    """LAB quick action."""

    label: str
    action: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiLabActionStatus:
    """Latest LAB control status."""

    action: str
    state: str
    detail: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UiLabConsolePayload:
    """Dedicated LAB CONSOLE payload."""

    nodes: tuple[UiLabNode, ...]
    edges: tuple[UiLabEdge, ...]
    telemetry: tuple[UiLabTelemetryItem, ...]
    terminal_tabs: tuple[UiLabTerminalTab, ...]
    action_buttons: tuple[UiLabActionButton, ...]
    action_status: UiLabActionStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "telemetry": [item.to_dict() for item in self.telemetry],
            "terminal_tabs": [tab.to_dict() for tab in self.terminal_tabs],
            "action_buttons": [button.to_dict() for button in self.action_buttons],
            "action_status": self.action_status.to_dict(),
        }


@dataclass(frozen=True)
class UiPagePayload:
    """UI page payload."""

    name: str
    title: str
    eyebrow: str = ""
    description: str = ""
    active_path: str = ""
    status_bar: Any | None = None
    traffic_chart: Any | None = None
    attack_chart: Any | None = None
    topology: Any | None = None
    feed: Any | None = None
    services: tuple[Any, ...] = ()
    stats: tuple[UiMetricCard, ...] = ()
    statuses: tuple[UiStatusTile, ...] = ()
    charts: tuple[UiChartModel, ...] = ()
    timeline: tuple[UiTimelineEntry, ...] = ()
    tables: tuple[UiTableSection, ...] = ()
    summary: dict[str, Any] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    cta: UiCommandCta | None = None
    stale: bool = False
    replay_safe: bool = True
    updated_at: str = ""
    lab_console: UiLabConsolePayload | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "eyebrow": self.eyebrow,
            "description": self.description,
            "active_path": self.active_path,
            "status_bar": self.status_bar.to_dict() if hasattr(self.status_bar, "to_dict") else self.status_bar,
            "traffic_chart": self.traffic_chart.to_dict() if hasattr(self.traffic_chart, "to_dict") else self.traffic_chart,
            "attack_chart": self.attack_chart.to_dict() if hasattr(self.attack_chart, "to_dict") else self.attack_chart,
            "topology": self.topology.to_dict() if hasattr(self.topology, "to_dict") else self.topology,
            "feed": self.feed.to_dict() if hasattr(self.feed, "to_dict") else self.feed,
            "services": [service.to_dict() if hasattr(service, "to_dict") else service for service in self.services],
            "stats": [card.to_dict() for card in self.stats],
            "statuses": [tile.to_dict() for tile in self.statuses],
            "charts": [chart.to_dict() for chart in self.charts],
            "timeline": [item.to_dict() for item in self.timeline],
            "tables": [table.to_dict() for table in self.tables],
            "summary": dict(self.summary),
            "timings": dict(self.timings),
            "cta": self.cta.to_dict() if self.cta is not None else None,
            "stale": self.stale,
            "replay_safe": self.replay_safe,
            "updated_at": self.updated_at,
            "lab_console": self.lab_console.to_dict() if self.lab_console is not None else None,
        }


@dataclass(frozen=True)
class UiPageSnapshot:
    """WebSocket snapshot payload."""

    status: str
    page: UiPagePayload

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "page": self.page.to_dict()}


@dataclass
class UiState:
    schema_version: str = SCHEMA_VERSION
    api_state: dict[str, Any] = field(default_factory=dict)
    synchronization_state: dict[str, Any] = field(default_factory=dict)
    replay_state: dict[str, Any] = field(default_factory=dict)
    graph_state: dict[str, Any] = field(default_factory=dict)
    pagination_state: dict[str, int] = field(default_factory=dict)
    refresh_metadata: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

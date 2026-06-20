"""Runtime query registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nsddos.runtime.query.models import QueryExecutor, RuntimeQuery, RuntimeQueryDependency
from nsddos.runtime.query.scopes import default_scopes


@dataclass(frozen=True)
class RuntimeQueryDefinition:
    """Registered query definition."""

    name: str
    scope: str
    executor: QueryExecutor
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    replay_safe: bool = True

    def to_query(self) -> RuntimeQuery:
        return RuntimeQuery(
            name=self.name,
            scope=self.scope,
            dependencies=self.dependencies,
            replay_safe=self.replay_safe,
        )


@dataclass
class RuntimeQueryRegistry:
    """Authoritative runtime query registry."""

    definitions: dict[str, RuntimeQueryDefinition] = field(default_factory=dict)
    scopes: dict[str, Any] = field(default_factory=default_scopes)

    def register(self, definition: RuntimeQueryDefinition) -> None:
        if definition.name in self.definitions:
            raise ValueError(f"duplicate query: {definition.name}")
        if definition.scope not in self.scopes:
            raise ValueError(f"unknown query scope: {definition.scope}")
        self.definitions[definition.name] = definition

    def dependencies(self) -> list[RuntimeQueryDependency]:
        edges: list[RuntimeQueryDependency] = []
        for definition in self.definitions.values():
            for dependency in definition.dependencies:
                edges.append(RuntimeQueryDependency(source=dependency, target=definition.name))
        return edges

    def ordered(self) -> list[RuntimeQueryDefinition]:
        ordered: list[RuntimeQueryDefinition] = []
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(name: str) -> None:
            if name in permanent:
                return
            if name in temporary:
                raise ValueError(f"query dependency cycle: {name}")
            if name not in self.definitions:
                raise ValueError(f"missing query dependency: {name}")
            temporary.add(name)
            for dependency in self.definitions[name].dependencies:
                visit(dependency)
            temporary.remove(name)
            permanent.add(name)
            ordered.append(self.definitions[name])

        for name in sorted(self.definitions):
            visit(name)
        return ordered


def default_query_registry() -> RuntimeQueryRegistry:
    """Build default query registry."""
    from nsddos.runtime.query.detection import query_detection
    from nsddos.runtime.query.evidence import query_evidence
    from nsddos.runtime.query.graph import query_graph
    from nsddos.runtime.query.live import (
        query_live_telemetry,
        query_provider_diagnostics,
        query_provider_discovery,
        query_provider_health,
    )
    from nsddos.runtime.query.ml import (
        query_ml_diagnostics,
        query_ml_infer,
        query_ml_retrain,
        query_ml_train,
    )
    from nsddos.runtime.query.policy import (
        query_policy_diagnostics,
        query_policy_evaluate,
        query_policy_history,
        query_policy_rollback,
    )
    from nsddos.runtime.query.mitigation import query_mitigation
    from nsddos.runtime.query.replay import query_replay
    from nsddos.runtime.query.snapshots import query_snapshots
    from nsddos.runtime.query.simulation import (
        query_simulation,
        query_simulation_diagnostics,
        query_simulation_replay,
        query_simulation_topology,
    )
    from nsddos.runtime.query.state import (
        query_convergence,
        query_drift,
        query_health,
        query_stability,
    )
    from nsddos.runtime.query.streaming import (
        query_stream_checkpoint,
        query_stream_diagnostics,
        query_stream_status,
    )
    from nsddos.runtime.query.service import query_service
    from nsddos.runtime.query.timeline import query_timeline
    from nsddos.runtime.query.verification import query_verification

    registry = RuntimeQueryRegistry()
    for definition in (
        RuntimeQueryDefinition("snapshots", "persistence", query_snapshots),
        RuntimeQueryDefinition("evidence", "evidence", query_evidence, ("snapshots",)),
        RuntimeQueryDefinition("verification", "verification", query_verification, ("evidence",)),
        RuntimeQueryDefinition("timeline", "temporal", query_timeline),
        RuntimeQueryDefinition("graph", "graph", query_graph, ("verification",)),
        RuntimeQueryDefinition("replay", "replay", query_replay, ("verification",)),
        RuntimeQueryDefinition("convergence", "convergence", query_convergence, ("verification",)),
        RuntimeQueryDefinition("drift", "temporal", query_drift, ("timeline",)),
        RuntimeQueryDefinition("stability", "temporal", query_stability, ("timeline",)),
        RuntimeQueryDefinition("health", "runtime", query_health),
        RuntimeQueryDefinition("service", "service", query_service, ("verification", "timeline")),
        RuntimeQueryDefinition("detection", "detection", query_detection, ("verification",)),
        RuntimeQueryDefinition("ml_infer", "ml", query_ml_infer, ("detection",)),
        RuntimeQueryDefinition("ml_diagnostics", "ml", query_ml_diagnostics, ("ml_infer",)),
        RuntimeQueryDefinition("ml_train", "ml", query_ml_train, ("ml_infer",)),
        RuntimeQueryDefinition("ml_retrain", "ml", query_ml_retrain, ("ml_train",)),
        RuntimeQueryDefinition("mitigation", "mitigation", query_mitigation, ("detection",)),
        RuntimeQueryDefinition("live_telemetry", "live", query_live_telemetry, ("verification",)),
        RuntimeQueryDefinition("provider_health", "provider", query_provider_health, ("live_telemetry",)),
        RuntimeQueryDefinition("provider_discovery", "provider", query_provider_discovery, ("live_telemetry",)),
        RuntimeQueryDefinition("provider_diagnostics", "provider", query_provider_diagnostics, ("live_telemetry",)),
        RuntimeQueryDefinition("simulation", "simulation", query_simulation, ("verification",)),
        RuntimeQueryDefinition("simulation_replay", "simulation", query_simulation_replay, ("simulation",)),
        RuntimeQueryDefinition("simulation_diagnostics", "simulation", query_simulation_diagnostics, ("simulation_replay",)),
        RuntimeQueryDefinition("simulation_topology", "simulation", query_simulation_topology, ("simulation",)),
        RuntimeQueryDefinition("stream_status", "streaming", query_stream_status, ("verification",)),
        RuntimeQueryDefinition("stream_checkpoint", "streaming", query_stream_checkpoint, ("stream_status",)),
        RuntimeQueryDefinition("stream_diagnostics", "streaming", query_stream_diagnostics, ("stream_checkpoint",)),
        RuntimeQueryDefinition("policy_evaluate", "policy", query_policy_evaluate, ("detection", "ml_infer")),
        RuntimeQueryDefinition("policy_history", "policy", query_policy_history, ("policy_evaluate",)),
        RuntimeQueryDefinition("policy_diagnostics", "policy", query_policy_diagnostics, ("policy_history",)),
        RuntimeQueryDefinition("policy_rollback", "policy", query_policy_rollback, ("policy_history",)),
    ):
        registry.register(definition)
    return registry

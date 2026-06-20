"""Authoritative producer registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from nsddos.runtime.producers.base import ProducerDefinition


@dataclass
class ProducerRegistry:
    producers: dict[str, ProducerDefinition] = field(default_factory=dict)

    def register(self, definition: ProducerDefinition) -> None:
        if definition.name in self.producers:
            raise ValueError(f"duplicate producer: {definition.name}")
        self.producers[definition.name] = definition

    def ordered(self) -> list[ProducerDefinition]:
        ordered: list[ProducerDefinition] = []
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(name: str) -> None:
            if name in permanent:
                return
            if name in temporary:
                raise ValueError(f"producer dependency cycle: {name}")
            if name not in self.producers:
                raise ValueError(f"missing producer dependency: {name}")
            temporary.add(name)
            for dependency in self.producers[name].dependencies:
                visit(dependency)
            temporary.remove(name)
            permanent.add(name)
            ordered.append(self.producers[name])

        for name in sorted(self.producers):
            visit(name)
        return ordered


def default_producer_registry() -> ProducerRegistry:
    registry = ProducerRegistry()
    definitions = (
        ProducerDefinition("runtime", "RuntimeRecord"),
        ProducerDefinition("topology", "RuntimeTopology", ("runtime",)),
        ProducerDefinition("datapath", "RuntimeDatapath", ("topology",)),
        ProducerDefinition("telemetry", "RuntimeTelemetry", ("runtime",)),
        ProducerDefinition("convergence", "RuntimeConvergence", ("topology", "datapath", "telemetry")),
        ProducerDefinition("verification", "RuntimeVerification", ("convergence",)),
        ProducerDefinition("evidence", "RuntimeEvidence", ("verification",)),
        ProducerDefinition("graph", "RuntimeGraph", ("evidence",)),
        ProducerDefinition("timeline", "RuntimeTimeline", ("runtime",)),
        ProducerDefinition("replay", "RuntimeReplay", ("timeline",)),
        ProducerDefinition("synchronization", "RuntimeSynchronization", ("replay",)),
        ProducerDefinition("sessions", "RuntimeSession", ("synchronization",)),
        ProducerDefinition("persistence", "RuntimeSnapshot", ("sessions",)),
        ProducerDefinition("environment", "RuntimeEnvironment", ("runtime",)),
        ProducerDefinition("capabilities", "RuntimeCapability", ("environment",)),
        ProducerDefinition("orchestration", "RuntimeTransition", ("capabilities",)),
        ProducerDefinition("collection", "RuntimeRecord", ("runtime",)),
        ProducerDefinition("analysis", "RuntimeRecord", ("collection",)),
        ProducerDefinition("normalization", "RuntimeRecord", ("analysis",)),
        ProducerDefinition("lifecycle", "RuntimeDrift", ("normalization",)),
        ProducerDefinition("transitions", "RuntimeTransition", ("lifecycle",)),
    )
    for definition in definitions:
        registry.register(definition)
    return registry

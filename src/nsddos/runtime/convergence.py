"""Runtime convergence validation."""

from __future__ import annotations

from nsddos.runtime.controller import normalize_controller_topology
from nsddos.runtime.models import ConvergenceState
from nsddos.runtime.openflow import correlate_openflow_ports
from nsddos.runtime.paths import correlate_paths
from nsddos.runtime.topology import correlate_topology


def validate_convergence(config: dict) -> ConvergenceState:
    """Return deterministic convergence state."""
    controller = normalize_controller_topology(config)
    topology = correlate_topology(config)
    openflow = correlate_openflow_ports(config)
    paths = correlate_paths(config)

    topology_agreement = topology.consistent
    datapath_agreement = not openflow.missing_ports and not openflow.duplicate_ports
    controller_agreement = not controller.stale_entities
    telemetry_agreement = not topology.missing_in_sflow and not paths.inconsistent_paths

    reasons = []
    if not topology_agreement:
        reasons.append("topology_disagreement")
    if not datapath_agreement:
        reasons.append("datapath_disagreement")
    if not controller_agreement:
        reasons.append("controller_stale_entities")
    if not telemetry_agreement:
        reasons.append("telemetry_disagreement")

    if topology_agreement and datapath_agreement and controller_agreement and telemetry_agreement:
        status = "converged"
    elif topology_agreement or datapath_agreement or controller_agreement or telemetry_agreement:
        status = "partially_converged"
    else:
        status = "diverged"

    stale_entities = sorted(set(controller.stale_entities + openflow.stale_ports))
    detail = (
        f"topology={topology_agreement} datapath={datapath_agreement} "
        f"controller={controller_agreement} telemetry={telemetry_agreement}"
    )
    return ConvergenceState(
        status=status,
        topology_agreement=topology_agreement,
        datapath_agreement=datapath_agreement,
        controller_agreement=controller_agreement,
        telemetry_agreement=telemetry_agreement,
        divergence_reasons=reasons,
        stale_entities=stale_entities,
        detail=detail,
    )

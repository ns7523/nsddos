"""Runtime evidence bundle export."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.config import ensure_runtime_directories
from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.correlation import correlate_runtime_events
from nsddos.runtime.controller import normalize_controller_topology
from nsddos.runtime.controller_state import controller_history_summary, record_controller_snapshot
from nsddos.runtime.capabilities import detect_runtime_capabilities
from nsddos.runtime.confidence import runtime_confidence_summary
from nsddos.runtime.convergence import validate_convergence
from nsddos.runtime.drift import detect_runtime_drift
from nsddos.runtime.environment import validate_bootstrap, validate_runtime_environment
from nsddos.runtime.execution_graph import build_execution_graph
from nsddos.runtime.flows import sample_flow_visibility, telemetry_freshness
from nsddos.runtime.graph import build_runtime_graph
from nsddos.runtime.identity import build_identity_map
from nsddos.runtime.interfaces import correlate_interfaces
from nsddos.runtime.models import EvidenceBundle, SCHEMA_VERSION
from nsddos.runtime.openflow import correlate_openflow_ports
from nsddos.runtime.paths import correlate_paths
from nsddos.runtime.persistence import atomic_write_json
from nsddos.runtime.profiles import detect_runtime_profile
from nsddos.runtime.reconcile import reconcile_runtime
from nsddos.runtime.reproducibility import analyze_reproducibility
from nsddos.runtime.replay import replay_execution_history
from nsddos.runtime.stability import analyze_runtime_stability
from nsddos.runtime.telemetry import build_runtime_snapshot
from nsddos.runtime.verification.engine import execute_runtime_verification
from nsddos.runtime.timeline import build_runtime_history_timeline, timeline_summary
from nsddos.runtime.topology import correlate_topology
from nsddos.runtime.transitions import load_transition_history
from nsddos.runtime.domain.evidence import RuntimeEvidence
from nsddos.runtime.domain.identifiers import evidence_id
from nsddos.runtime.domain.serialization import to_canonical_dict


def export_evidence_bundle(config: dict) -> EvidenceBundle:
    """Write evidence bundle with JSON + text summary."""
    ensure_runtime_directories()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_dir = RUNTIME_DIR / "evidence" / timestamp
    bundle_dir.mkdir(parents=True, exist_ok=True)

    snapshot = build_runtime_snapshot(config)
    controller_snapshot = record_controller_snapshot(config)
    controller = normalize_controller_topology(config)
    controller_history = controller_history_summary(config)
    convergence = validate_convergence(config)
    profile = detect_runtime_profile()
    capabilities = detect_runtime_capabilities()
    environment = validate_runtime_environment(config)
    reproducibility = analyze_reproducibility(config)
    bootstrap = validate_bootstrap(config)
    execution_graph = build_execution_graph(config)
    execution_replay = replay_execution_history()
    timeline = build_runtime_history_timeline()
    transitions = load_transition_history()
    correlation = correlate_runtime_events()
    stability = analyze_runtime_stability()
    identity = build_identity_map(config)
    interfaces = correlate_interfaces(config)
    openflow = correlate_openflow_ports(config)
    paths = correlate_paths(config)
    topology = correlate_topology(config)
    reconciliation = reconcile_runtime(config)
    drift = detect_runtime_drift(config)
    graph = build_runtime_graph(config)
    flows = sample_flow_visibility(config)
    freshness = telemetry_freshness(config)
    verification = execute_runtime_verification(config)
    confidence = runtime_confidence_summary(topology, flows, freshness, verification, reconciliation)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "snapshot": snapshot,
        "controller_snapshot": controller_snapshot,
        "controller_history": controller_history,
        "controller_topology": controller.to_dict(),
        "runtime_profile": profile.to_dict(),
        "capabilities": capabilities.to_dict(),
        "environment": environment.to_dict(),
        "reproducibility": reproducibility.to_dict(),
        "bootstrap": bootstrap,
        "execution_graph": execution_graph,
        "execution_replay": execution_replay,
        "convergence": convergence.to_dict(),
        "timeline": [item.to_dict() for item in timeline],
        "timeline_summary": timeline_summary(timeline),
        "transitions": transitions,
        "correlation": correlation,
        "stability": stability,
        "identity": identity.to_dict(),
        "interfaces": interfaces.to_dict(),
        "openflow": openflow.to_dict(),
        "paths": paths.to_dict(),
        "topology": topology.to_dict(),
        "reconciliation": reconciliation.to_dict(),
        "drift": [item.to_dict() for item in drift],
        "graph": graph,
        "flows": flows.to_dict(),
        "freshness": freshness.to_dict(),
        "verification": [item.to_dict() for item in verification],
        "confidence": confidence,
        "typed_evidence": [
            to_canonical_dict(
                RuntimeEvidence(
                    evidence_id=evidence_id(f"{timestamp}:snapshot"),
                    reference=str(snapshot.get("timestamp", timestamp)),
                    lineage=(
                        str(convergence.status),
                        str(profile.name),
                        str(environment.status),
                    ),
                    detail="verification_convergence_runtime_lineage",
                )
            )
        ],
    }
    snapshot_path = bundle_dir / "evidence.json"
    summary_path = bundle_dir / "summary.txt"
    atomic_write_json(snapshot_path, payload)
    summary_path.write_text(
        "\n".join(
            [
                "NS-DDoS Evidence Bundle",
                f"timestamp={timestamp}",
                f"topology={confidence['topology']}",
                f"telemetry={confidence['telemetry']}",
                f"flows={confidence['flows']}",
                f"datapath={confidence.get('datapath', 'unknown')}",
                f"provider_agreement={confidence['provider_agreement']}",
                f"convergence={convergence.status}",
                f"stability={stability['classification']}",
                f"profile={profile.name}",
                f"environment={environment.status}",
                f"reproducibility={reproducibility.status}",
                f"pipeline={stability.get('pipeline', 'unknown')}",
                f"reductions={','.join(confidence.get('confidence_reductions', []))}",
            ]
        ),
        encoding="utf-8",
    )
    return EvidenceBundle(
        timestamp=timestamp,
        bundle_dir=str(bundle_dir),
        snapshot_file=str(snapshot_path),
        summary_file=str(summary_path),
    )

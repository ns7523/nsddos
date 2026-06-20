"""Deterministic release candidate packaging engine."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from nsddos.constants import PROJECT_ROOT, RUNTIME_DIR
from nsddos.dashboard import latest_dashboard_evaluation
from nsddos.deployment import latest_deployment_payload
from nsddos.distributed import latest_distributed_evaluation
from nsddos.release.artifacts import artifacts_payload, build_artifacts
from nsddos.release.benchmark import build_benchmark_result
from nsddos.release.chaos import build_chaos_result
from nsddos.release.compliance import build_compliance_result
from nsddos.release.contracts import PackageMetadata, ReleaseCandidateEvaluation, ReleaseSourceBundle
from nsddos.release.dependencies import audit_dependencies
from nsddos.release.diagnostics import build_release_diagnostics
from nsddos.release.fault_injection import build_fault_injection_result
from nsddos.release.hardening import build_hardening_result
from nsddos.release.loadtest import build_load_test_result
from nsddos.release.profiling import build_profiling_result
from nsddos.release.registry import latest_release_candidate
from nsddos.release.release_notes import build_release_notes
from nsddos.release.security_audit import build_security_audit_result
from nsddos.release.stresstest import build_stress_test_result
from nsddos.release.validation import validate_release_candidate
from nsddos.runtime.profiles import detect_runtime_profile
from nsddos.runtime.persistence import atomic_write_json, locked_persistence_scope
from nsddos.runtime.verification.replay import replay_verification_runs

RELEASE_DIR = RUNTIME_DIR / "release"


def _load_sources(project_root: Path = PROJECT_ROOT) -> ReleaseSourceBundle:
    deployment = latest_deployment_payload()
    distributed = latest_distributed_evaluation()
    dashboard = latest_dashboard_evaluation()
    verification_runs = replay_verification_runs(limit=1).get("runs", [])
    latest_run = verification_runs[-1] if verification_runs else {}
    verification_results = tuple(item for item in latest_run.get("results", []) if isinstance(item, dict))
    profile = detect_runtime_profile()
    profile_name = profile.get("name", "unknown") if isinstance(profile, dict) else getattr(profile, "name", "unknown")
    pyproject_path = project_root / "pyproject.toml"
    dependency_lines: list[str] = []
    optional_lines: list[str] = []
    if pyproject_path.exists():
        section = ""
        for raw_line in pyproject_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("[project.optional-dependencies]"):
                section = "optional"
                continue
            if line.startswith("[project]"):
                section = "project"
                continue
            if line.startswith("[") and not line.startswith("[project"):
                section = ""
            if line.startswith('"') and line.endswith('",'):
                if section == "project":
                    dependency_lines.append(line.strip('",'))
                elif section == "optional":
                    optional_lines.append(line.strip('",'))
    manifests = tuple(
        str(path.relative_to(project_root))
        for path in (
            project_root / "deployment" / "docker" / "Dockerfile.prod",
            project_root / "deployment" / "docker" / "docker-compose.prod.yml",
            project_root / "deployment" / "kubernetes" / "deployment.yaml",
            project_root / "deployment" / "kubernetes" / "service.yaml",
            project_root / "deployment" / "kubernetes" / "hpa.yaml",
            project_root / "deployment" / "kubernetes" / "configmap.yaml",
            project_root / "deployment" / "kubernetes" / "secrets.yaml",
            project_root / "deployment" / "kubernetes" / "networkpolicy.yaml",
        )
        if path.exists()
    )
    return ReleaseSourceBundle(
        active_nodes=int(distributed.get("active_nodes", 1) or 1),
        cluster_health=str(distributed.get("cluster_health", "degraded")),
        dashboard_health=str(dashboard.get("dashboard_health", "degraded")),
        active_alerts=int(dashboard.get("active_alerts", 0)),
        stream_throughput=float(dashboard.get("stream_throughput", 0.0)),
        ml_confidence=float(dashboard.get("ml_confidence", 0.0)),
        policy_events=int(dashboard.get("policy_events", 0)),
        mitigation_events=int(dashboard.get("mitigation_events", 0)),
        deployment_state=str(deployment.get("deployment_state", "degraded_dry_run")),
        service_health=str(deployment.get("service_health", deployment.get("health", {}).get("service_health", "degraded"))),
        rollback_available=bool(deployment.get("rollback_available", deployment.get("rollback_state", {}).get("rollback_available", False))),
        missing_secret_count=int(
            deployment.get("diagnostics", {}).get("missing_secret_count", len(deployment.get("secret_contract", {}).get("missing_keys", [])))
        ),
        warning_count=sum(1 for item in verification_results if item.get("status") == "warn"),
        failure_count=sum(1 for item in verification_results if item.get("status") == "fail"),
        runtime_profile=str(profile_name),
        provider_burst_supported=bool(dashboard),
        package_dependencies=tuple(dependency_lines),
        optional_dependencies=tuple(optional_lines),
        manifests=manifests,
    )


def _release_id(release_version: str, environment: str, timestamp: datetime) -> str:
    digest = hashlib.sha256(f"{release_version}:{environment}:{timestamp.isoformat()}".encode("utf-8")).hexdigest()[:16]
    return f"release:{digest}"


def _package_metadata(release_id: str, config: dict, sources: ReleaseSourceBundle) -> PackageMetadata:
    release_version = str(config.get("release", {}).get("version", "1.0.0-rc1"))
    prefix = str(config.get("release", {}).get("artifact_prefix", "nsddos-release"))
    bundle_name = f"{prefix}-{release_version}"
    archive_name = f"{bundle_name}.tar.gz"
    return PackageMetadata(
        package_id=f"{release_id}:package",
        release_version=release_version,
        bundle_name=bundle_name,
        deployment_bundle=sources.manifests,
        archive_name=archive_name,
        ready=bool(sources.manifests),
    )


def _release_state(config: dict, evaluation: ReleaseCandidateEvaluation) -> str:
    release_config = config.get("release", {})
    benchmark_min = float(release_config.get("benchmark_min_score", 0.70))
    security_min = float(release_config.get("security_min_score", 0.80))
    performance_min = float(release_config.get("performance_min_score", 0.70))
    stress_min = float(release_config.get("stress_min_score", 0.65))
    if (
        evaluation.compliance_state == "compliant"
        and evaluation.security_score >= security_min
        and evaluation.dependencies.dependency_health == "healthy"
        and evaluation.hardening_state in {"strict", "degraded"}
    ):
        return "release_ready"
    if (
        evaluation.benchmark_score >= benchmark_min
        and evaluation.security_score >= security_min
        and evaluation.performance_score >= performance_min
        and evaluation.stress_test_score >= stress_min
        and evaluation.hardening_state == "strict"
        and evaluation.compliance_state == "compliant"
        and evaluation.dependencies.dependency_health != "failed"
    ):
        return "release_ready"
    if evaluation.compliance_state == "failed" or evaluation.security_score < 0.4:
        return "release_blocked"
    return "release_review"


def _persist(evaluation: ReleaseCandidateEvaluation) -> None:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    payload = evaluation.to_dict()
    stamp = evaluation.timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    with locked_persistence_scope(RELEASE_DIR) as lock_scope:
        atomic_write_json(RELEASE_DIR / f"release-{stamp}.json", payload, lock_scope=lock_scope)
        atomic_write_json(RELEASE_DIR / "latest.json", payload, lock_scope=lock_scope)
        atomic_write_json(RELEASE_DIR / "benchmark.json", evaluation.benchmark.to_dict(), lock_scope=lock_scope)
        atomic_write_json(RELEASE_DIR / "artifacts.json", artifacts_payload(evaluation), lock_scope=lock_scope)
        atomic_write_json(RELEASE_DIR / "package.json", evaluation.package_metadata.to_dict(), lock_scope=lock_scope)
        atomic_write_json(RELEASE_DIR / "release_notes.json", evaluation.release_notes.to_dict(), lock_scope=lock_scope)
        atomic_write_json(RELEASE_DIR / "diagnostics.json", evaluation.diagnostics.to_dict(), lock_scope=lock_scope)
        atomic_write_json(RELEASE_DIR / "security_audit.json", evaluation.security_audit.to_dict(), lock_scope=lock_scope)


def generate_release_candidate(config: dict, environment: str = "prod") -> ReleaseCandidateEvaluation:
    """Generate deterministic release candidate evaluation."""
    started = perf_counter()
    timestamp = datetime.now(timezone.utc)
    sources = _load_sources()
    benchmark = build_benchmark_result(config, sources)
    load_test = build_load_test_result(config, sources)
    stress_test = build_stress_test_result(config, sources)
    chaos = build_chaos_result(sources)
    fault_injection = build_fault_injection_result(sources)
    dependency_audit = audit_dependencies()
    security_audit = build_security_audit_result(config, sources, dependency_audit)
    profiling = build_profiling_result(benchmark, load_test, stress_test)
    hardening = build_hardening_result(config, sources)
    compliance = build_compliance_result(sources, hardening)
    release_version = str(config.get("release", {}).get("version", "1.0.0-rc1"))
    release_id = _release_id(release_version, environment, timestamp)
    package_metadata = _package_metadata(release_id, config, sources)
    artifacts = build_artifacts(
        package_metadata,
        release_id,
        str(config.get("release", {}).get("checksum_algorithm", "sha256")),
    )
    release_notes = build_release_notes(
        release_version,
        benchmark.benchmark_score,
        security_audit,
        hardening,
        compliance,
    )
    diagnostics = build_release_diagnostics(
        (perf_counter() - started) * 1000.0,
        benchmark.benchmark_score,
        stress_test,
        dependency_audit,
        security_audit,
    )
    evaluation = ReleaseCandidateEvaluation(
        release_id=release_id,
        release_version=release_version,
        benchmark_score=benchmark.benchmark_score,
        load_test_score=load_test.load_test_score,
        stress_test_score=stress_test.stress_test_score,
        security_score=security_audit.security_score,
        dependency_health=dependency_audit.dependency_health,
        performance_score=profiling.performance_score,
        hardening_state=hardening.hardening_state,
        compliance_state=compliance.compliance_state,
        release_state="release_review",
        timestamp=timestamp,
        environment=environment,
        benchmark=benchmark,
        load_test=load_test,
        stress_test=stress_test,
        chaos=chaos,
        fault_injection=fault_injection,
        dependencies=dependency_audit,
        security_audit=security_audit,
        profiling=profiling,
        hardening=hardening,
        compliance=compliance,
        package_metadata=package_metadata,
        artifacts=artifacts,
        release_notes=release_notes,
        diagnostics=diagnostics,
    )
    evaluation = ReleaseCandidateEvaluation(
        release_id=evaluation.release_id,
        release_version=evaluation.release_version,
        benchmark_score=evaluation.benchmark_score,
        load_test_score=evaluation.load_test_score,
        stress_test_score=evaluation.stress_test_score,
        security_score=evaluation.security_score,
        dependency_health=evaluation.dependency_health,
        performance_score=evaluation.performance_score,
        hardening_state=evaluation.hardening_state,
        compliance_state=evaluation.compliance_state,
        release_state=_release_state(config, evaluation),
        timestamp=evaluation.timestamp,
        schema_version=evaluation.schema_version,
        environment=evaluation.environment,
        benchmark=evaluation.benchmark,
        load_test=evaluation.load_test,
        stress_test=evaluation.stress_test,
        chaos=evaluation.chaos,
        fault_injection=evaluation.fault_injection,
        dependencies=evaluation.dependencies,
        security_audit=evaluation.security_audit,
        profiling=evaluation.profiling,
        hardening=evaluation.hardening,
        compliance=evaluation.compliance,
        package_metadata=evaluation.package_metadata,
        artifacts=evaluation.artifacts,
        release_notes=evaluation.release_notes,
        diagnostics=evaluation.diagnostics,
    )
    errors = validate_release_candidate(evaluation)
    if errors:
        raise ValueError(f"release evaluation invalid: {','.join(errors)}")
    _persist(evaluation)
    return evaluation


def release_benchmark(config: dict, environment: str = "prod") -> dict:
    """Return latest benchmark payload."""
    return generate_release_candidate(config, environment=environment).benchmark.to_dict()


def release_security_audit(config: dict, environment: str = "prod") -> dict:
    """Return latest security-audit payload."""
    return generate_release_candidate(config, environment=environment).security_audit.to_dict()


def release_diagnostics(config: dict, environment: str = "prod") -> dict:
    """Return latest release diagnostics payload."""
    return generate_release_candidate(config, environment=environment).diagnostics.to_dict()


def latest_or_generate_release_candidate(config: dict, environment: str = "prod") -> dict:
    """Return latest release payload or generate one."""
    latest = latest_release_candidate()
    if latest and latest.get("environment") == environment:
        return latest
    return generate_release_candidate(config, environment=environment).to_dict()

"""CLI entrypoint for NS-DDoS."""

from __future__ import annotations

import json
import re
import subprocess
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from shutil import which

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nsddos.bootstrap import render_welcome_screen, run_doctor_command, run_reset_command, run_setup_wizard, run_startup_command
from nsddos.bootstrap.assets import download_runtime_assets
from nsddos.bootstrap.doctor import ensure_doctor_success
from nsddos.bootstrap.reset import ensure_reset_success
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.bootstrap.ui_launcher import launch_ui_background, replace_listener_on_port
from nsddos.config import load_config, load_runtime_state, write_runtime_state
from nsddos.constants import APP_NAME, APP_VERSION, CONFIG_PATH, STATE_PATH
from nsddos.dashboard import dashboard_alerts, dashboard_diagnostics, dashboard_report, generate_dashboard_state
from nsddos.distributed import distributed_failover_plan, distributed_health, orchestrate_cluster_runtime
from nsddos.distributed.diagnostics import diagnostics_to_rows as distributed_diagnostics_to_rows
from nsddos.deployment import deploy_runtime_stack, deployment_health, rollback_runtime_stack
from nsddos.deployment.diagnostics import diagnostics_to_rows
from nsddos.docker_manager import DockerManager
from nsddos.health import collect_static_health, get_health_report
from nsddos.logger import setup_logging
from nsddos.release import generate_release_candidate, release_benchmark, release_diagnostics, release_security_audit, validate_release_candidate
from nsddos.runtime.controller import normalize_controller_topology
from nsddos.runtime.capabilities import detect_runtime_capabilities
from nsddos.runtime.correlation import correlate_runtime_events
from nsddos.runtime.convergence import validate_convergence
from nsddos.runtime.evidence import export_evidence_bundle
from nsddos.runtime.environment import validate_bootstrap, validate_runtime_environment
from nsddos.runtime.events import build_runtime_timeline, emit_runtime_event
from nsddos.runtime.execution_graph import export_execution_graph
from nsddos.runtime.flows import validate_traffic
from nsddos.runtime.graph import (
    build_runtime_graph,
    export_runtime_bundle,
    export_runtime_history,
    export_runtime_graph,
    export_runtime_relationships,
)
from nsddos.runtime.identity import build_identity_map
from nsddos.runtime.interfaces import correlate_interfaces
from nsddos.runtime.lifecycle import start_lab_runtime, stop_lab_runtime
from nsddos.runtime.models import RuntimeState, SCHEMA_VERSION
from nsddos.runtime.openflow import correlate_openflow_ports
from nsddos.runtime.orchestrator import execute_pipeline, shutdown_pipeline, use_runtime_preset
from nsddos.runtime.paths import correlate_paths
from nsddos.runtime.persistence import atomic_write_json, recover_json
from nsddos.runtime.pipeline import build_execution_plan
from nsddos.runtime.profiles import detect_runtime_profile
from nsddos.runtime.query.engine import execute_query, explain_query_system
from nsddos.runtime.query.models import RuntimeQuery, RuntimeQueryFilter, RuntimeQueryPagination
from nsddos.runtime.reconcile import reconcile_runtime
from nsddos.runtime.reproducibility import analyze_reproducibility
from nsddos.runtime.replay import replay_execution_history
from nsddos.runtime.collection_layer import collect_runtime_bundle
from nsddos.runtime.analysis_layer import aggregate_runtime
from nsddos.runtime.attack import run_live_attack_suite
from nsddos.runtime.cache import cache_summary
from nsddos.runtime.stability import analyze_runtime_stability
from nsddos.runtime.telemetry import build_runtime_snapshot, compare_snapshots, snapshot_file_path, verify_runtime
from nsddos.runtime.timeline import build_runtime_history_timeline
from nsddos.runtime.verification.engine import explain_verification
from nsddos.runtime.verification.replay import replay_verification_runs
from nsddos.runtime.domain.registry import default_domain_registry
from nsddos.runtime.domain.validation import (
    validate_contract_payload,
    validate_identifier_stability,
    validate_relationship_integrity,
)
from nsddos.runtime.detection import evaluate_detection, explain_detection, latest_detection_evidence
from nsddos.runtime.detection.validation import validate_detection_evaluation
from nsddos.runtime.mitigation import enforce_mitigation, evaluate_mitigation, explain_mitigation, latest_mitigation_evidence
from nsddos.runtime.mitigation.validation import validate_mitigation_evaluation
from nsddos.runtime.ml import evaluate_ml_detection, latest_ml_evaluation, retrain_ml_model, train_ml_model
from nsddos.runtime.providers.live import (
    build_provider_diagnostics,
    collect_live_telemetry,
    collect_provider_health,
    discover_runtime_providers,
)
from nsddos.runtime.policy import evaluate_dynamic_policy, latest_history_payload, latest_policy_evaluation, rollback_dynamic_policy
from nsddos.runtime.simulation import build_simulation_diagnostics, generate_attack_traffic
from nsddos.runtime.streaming import latest_checkpoint, latest_streaming_evaluation, process_stream_events
from nsddos.runtime.producers import default_producer_registry, produce_records
from nsddos.runtime.freshness.consistency import validate_consistency
from nsddos.runtime.freshness.diagnostics import explain_freshness
from nsddos.runtime.freshness.lineage import propagate_state
from nsddos.runtime.freshness.replay import validate_replay_freshness
from nsddos.runtime.freshness.validation import validate_freshness_payload
from nsddos.service.manager import RuntimeServiceManager

app = typer.Typer(
    name=APP_NAME,
    help="NS-DDoS command line interface.",
    no_args_is_help=False,
    invoke_without_command=True,
)
lab_app = typer.Typer(help="Manage local lab runtime.")
runtime_app = typer.Typer(help="Inspect runtime evidence and timeline.")
api_app = typer.Typer(help="Manage read-only runtime API.")
service_app = typer.Typer(help="Manage persistent runtime service.")
ui_app = typer.Typer(help="Manage operational observability UI.")
bootstrap_app = typer.Typer(help="Manage runtime asset bootstrap.")
app.add_typer(lab_app, name="lab")
app.add_typer(runtime_app, name="runtime")
app.add_typer(api_app, name="api")
app.add_typer(service_app, name="service")
app.add_typer(ui_app, name="ui")
app.add_typer(bootstrap_app, name="bootstrap")
console = Console()


@app.callback()
def root(ctx: typer.Context) -> None:
    """Render premium welcome when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        render_welcome_screen(console)


def _bootstrap() -> dict:
    """Prepare config and logging for command execution."""
    try:
        config = load_config()
        setup_logging(config.get("logging", {}).get("level", "INFO"))
        return config
    except Exception as exc:
        console.print(f"[bold red]Bootstrap failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def _render_health_table(title: str, results: list) -> None:
    """Render health results."""
    table = Table(title=title)
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for result in results:
        table.add_row(
            result.name,
            "[green]OK[/green]" if result.ok else "[red]FAIL[/red]",
            result.detail,
        )
    console.print(table)


def _render_verification_table(title: str, results: list) -> None:
    """Render verification-style results."""
    table = Table(title=title)
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Category")
    table.add_column("Detail")
    colors = {"pass": "green", "fail": "red", "warn": "yellow", "stale": "magenta"}
    for result in results:
        color = colors.get(result.status, "white")
        table.add_row(result.name, f"[{color}]{result.status.upper()}[/{color}]", result.category, result.detail)
    console.print(table)


def _render_mapping_table(title: str, rows: list[tuple[str, str]]) -> None:
    """Render simple mapping table."""
    table = Table(title=title)
    table.add_column("Field")
    table.add_column("Value")
    for left, right in rows:
        table.add_row(left, right)
    console.print(table)


def _verification_summary(results: list) -> tuple[int, int, int, int]:
    """Return pass, fail, warn, stale counts."""
    passed = sum(1 for result in results if result.status == "pass")
    failed = sum(1 for result in results if result.status == "fail")
    warned = sum(1 for result in results if result.status == "warn")
    stale = sum(1 for result in results if result.status == "stale")
    return passed, failed, warned, stale


def _open_browser(url: str) -> None:
    """Open browser shortly after CLI returns control."""

    threading.Timer(0.75, lambda: webbrowser.open(url)).start()


def _dashboard_url(base_url: str) -> str:
    """Return operator dashboard URL."""

    return f"{base_url.rstrip('/')}/ui"


def _render_failed_health(results: list) -> tuple[str, ...]:
    """Render failing health rows and return names."""

    failed = [result for result in results if not result.ok]
    if failed:
        _render_health_table("NS-DDoS Demo Prerequisites", results)
    return tuple(result.name for result in failed)


def _parse_trycloudflare_url(line: str) -> str | None:
    """Extract public trycloudflare URL from output line."""

    match = re.search(r"https://[A-Za-z0-9.-]+\.trycloudflare\.com", line)
    return match.group(0) if match else None


def _cloudflared_install_hint() -> str:
    """Return short install guidance for Cloudflare Tunnel."""

    return "Install `cloudflared` first. macOS: `brew install cloudflared`. Docs: docs/installation.md#cloudflare-tunnel"


def _render_query_result(title: str, result) -> None:
    """Render runtime query result."""
    table = Table(title=title)
    table.add_column("ID")
    table.add_column("Detail")
    for item in result.items:
        identifier = str(item.get("id", item.get("path", "item")))
        detail = ", ".join(
            f"{key}={value}"
            for key, value in item.items()
            if key != "id" and isinstance(value, (str, int, float, bool))
        )
        table.add_row(identifier, detail[:160])
    console.print(table)
    _render_mapping_table(
        "Query Summary",
        [
            ("query", result.query.name),
            ("scope", result.query.scope),
            ("items", f"{len(result.items)}/{result.total}"),
            ("duration_ms", f"{result.duration_ms:.2f}"),
            ("cache_key", str(result.cache.get("key", ""))),
        ],
    )


def _query(name: str, scope: str, limit: int = 25, field: str | None = None, value: str | None = None):
    filters = ()
    if field and value is not None:
        filters = (RuntimeQueryFilter(field=field, value=value, operator="contains"),)
    return RuntimeQuery(name=name, scope=scope, filters=filters, pagination=RuntimeQueryPagination(limit=limit))


@lab_app.command("start")
def lab_start() -> None:
    """Start NS-DDoS lab runtime."""
    config = _bootstrap()
    static_results = collect_static_health()
    if not all(result.ok for result in static_results):
        _render_health_table("NS-DDoS Static Health", static_results)
        console.print("[bold red]Environment validation failed.[/bold red]")
        raise typer.Exit(code=1)

    try:
        start_lab_runtime(config)
    except typer.Exit:
        raise
    except RuntimeError as exc:
        emit_runtime_event("lab.start", "failed", "Lab start failed.", {"detail": str(exc)})
        console.print(f"[bold red]Lab start failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        Panel.fit(
            f"[bold green]NS-DDoS lab started[/bold green]\n"
            f"Config: {CONFIG_PATH}\n"
            f"Dashboard port: {config['dashboard_port']}",
            title="Lab Start",
        )
    )


@lab_app.command("stop")
def lab_stop() -> None:
    """Stop NS-DDoS lab runtime."""
    config = _bootstrap()
    try:
        stop_lab_runtime(config)
    except typer.Exit:
        raise
    console.print(Panel.fit("[bold yellow]NS-DDoS lab stopped[/bold yellow]", title="Lab Stop"))


@lab_app.command("status")
def lab_status() -> None:
    """Show NS-DDoS lab runtime status."""
    _bootstrap()
    manager = DockerManager()
    runtime_state = load_runtime_state()
    service_status = manager.get_service_status()

    table = Table(title="NS-DDoS Lab Status")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("stack_running", str(runtime_state.stack_running))
    table.add_row("started_at", str(runtime_state.started_at))
    table.add_row("updated_at", str(runtime_state.updated_at))
    table.add_row("topology_state", runtime_state.topology_state)
    table.add_row("topology_pid", str(runtime_state.topology_pid))
    table.add_row("controller_connected", str(runtime_state.controller_connected))
    table.add_row("compose_file", service_status.get("compose_file", ""))
    table.add_row("services", str([service.name for service in runtime_state.services]))
    console.print(table)

    if runtime_state.services:
        service_table = Table(title="Services")
        service_table.add_column("Service")
        service_table.add_column("Status")
        service_table.add_column("Healthy")
        service_table.add_column("Container")
        for service in runtime_state.services:
            service_table.add_row(
                service.name,
                service.status,
                "yes" if service.healthy else "no",
                service.container_id or "",
            )
        console.print(service_table)


@lab_app.command("logs")
def lab_logs(service: str | None = typer.Argument(None)) -> None:
    """Stream lab logs."""
    _bootstrap()
    manager = DockerManager()
    manager.stream_logs(service=service)


@lab_app.command("snapshot")
def lab_snapshot() -> None:
    """Export runtime snapshot JSON."""
    config = _bootstrap()
    snapshot = build_runtime_snapshot(config)
    path = snapshot_file_path()
    atomic_write_json(path, snapshot)
    console.print(
        Panel.fit(
            f"[bold cyan]Runtime snapshot written[/bold cyan]\n{path}",
            title="Lab Snapshot",
        )
    )


@lab_app.command("compare-snapshots")
def lab_compare_snapshots(
    snapshot_a: Path = typer.Argument(..., exists=True, readable=True),
    snapshot_b: Path = typer.Argument(..., exists=True, readable=True),
) -> None:
    """Compare two runtime snapshots."""
    _bootstrap()
    comparison = compare_snapshots(snapshot_a, snapshot_b)
    table = Table(title="Snapshot Comparison")
    table.add_column("Field")
    table.add_column("Changed")
    for field in (
        "controller_drift",
        "convergence_drift",
        "profile_drift",
        "capability_drift",
        "environment_drift",
        "reproducibility_drift",
        "execution_plan_drift",
        "execution_graph_drift",
        "execution_replay_drift",
        "stability_drift",
        "timeline_drift",
        "identity_drift",
        "datapath_drift",
        "path_drift",
        "topology_changed",
        "provider_drift",
        "telemetry_changed",
        "flow_visibility_changed",
        "reconciliation_changed",
        "drift_changed",
        "confidence_changed",
    ):
        table.add_row(field, "yes" if comparison.get(field) else "no")
    console.print(table)
    runtime_transition = comparison.get("transition_summary", {}).get("runtime", {})
    console.print(
        Panel.fit(
            f"from: {runtime_transition.get('from_state', 'unknown')}\n"
            f"to: {runtime_transition.get('to_state', 'unknown')}\n"
            f"affected: {', '.join(runtime_transition.get('affected_entities', [])) or 'none'}",
            title="Transition Summary",
        )
    )
    console.print(
        Panel.fit(
            f"snapshot_a: {comparison['snapshot_a']}\n"
            f"snapshot_b: {comparison['snapshot_b']}",
            title="Snapshot Inputs",
        )
    )


@app.command()
def health(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Show platform health checks."""
    _bootstrap()
    if verbose:
        report = get_health_report(verbose=True)
        _render_health_table("NS-DDoS Static Health", report["static"])
        _render_health_table("NS-DDoS Runtime Health", report["runtime"])
        return
    report = get_health_report(verbose=False)["flat"]
    flattened = [
        type("HealthRow", (), {"name": key, "ok": value, "detail": ""})()
        for key, value in report.items()
    ]
    _render_health_table("NS-DDoS Health", flattened)


@app.command()
def verify() -> None:
    """Run layered runtime verification."""
    config = _bootstrap()
    results = verify_runtime(config)
    _render_verification_table("NS-DDoS Verify", results)
    passed, failed, warned, stale = _verification_summary(results)
    total = len(results)
    console.print(
        Panel.fit(
            f"Passed: {passed}\nFailed: {failed}\nWarnings: {warned}\nStale: {stale}\nReadiness: {passed}/{total}",
            title="Verification Summary",
        )
    )
    if failed:
        emit_runtime_event("verify", "failed", "Runtime verification failed.", {"failed": failed})
        raise typer.Exit(code=1)
    if warned or stale:
        emit_runtime_event(
            "verify",
            "warning" if warned else "stale",
            "Runtime verification completed with warnings.",
            {"warnings": warned, "stale": stale},
        )
    else:
        emit_runtime_event("verify", "completed", "Runtime verification passed.")


@app.command()
def doctor(deep: bool = typer.Option(False, "--deep")) -> None:
    """Run doctor diagnostics and self-healing."""
    _ = deep
    result = run_doctor_command(console)
    ensure_doctor_success(result)


@app.command()
def reset() -> None:
    """Reset runtime/session/log state while preserving config."""
    result = run_reset_command(console)
    ensure_reset_success(result)


@runtime_app.command("timeline")
def runtime_timeline() -> None:
    """Show ordered runtime timeline."""
    _bootstrap()
    events = build_runtime_timeline()
    table = Table(title="NS-DDoS Runtime Timeline")
    table.add_column("Timestamp")
    table.add_column("Event")
    table.add_column("Status")
    table.add_column("Delta ms")
    table.add_column("Message")
    for event in events:
        delta = "" if event.duration_ms is None else f"{event.duration_ms:.0f}"
        table.add_row(event.timestamp, event.event_type, event.status, delta, event.message)
    console.print(table)


@runtime_app.command("explain-timeline")
def runtime_explain_timeline() -> None:
    """Explain temporal runtime evolution."""
    _bootstrap()
    events = build_runtime_history_timeline()
    table = Table(title="NS-DDoS Runtime History")
    table.add_column("Timestamp")
    table.add_column("Event")
    table.add_column("Convergence")
    table.add_column("Drift")
    table.add_column("Topology")
    table.add_column("Affected")
    for event in events:
        table.add_row(
            event.timestamp,
            event.event_type,
            event.convergence_impact,
            event.drift_impact,
            event.topology_impact,
            ", ".join(event.affected_entities) or "none",
        )
    console.print(table)


@runtime_app.command("explain-correlation")
def runtime_explain_correlation() -> None:
    """Explain deterministic event correlation."""
    _bootstrap()
    correlation = correlate_runtime_events()
    table = Table(title="NS-DDoS Runtime Correlation")
    table.add_column("Index")
    table.add_column("Cause")
    table.add_column("Affected")
    table.add_column("Hints")
    for index, group in enumerate(correlation.get("groups", []), start=1):
        table.add_row(
            str(index),
            str(group.get("cause", "unknown")),
            ", ".join(group.get("affected_entities", [])) or "none",
            ", ".join(group.get("causality_hints", [])) or "none",
        )
    console.print(table)
    _render_mapping_table(
        "Correlation Summary",
        [
            ("patterns", ", ".join(correlation.get("recurring_instability_patterns", [])) or "none"),
            ("timeline_events", str(correlation.get("timeline_events", 0))),
            ("transition_events", str(correlation.get("transition_events", 0))),
        ],
    )


@runtime_app.command("explain-stability")
def runtime_explain_stability() -> None:
    """Explain runtime stability state."""
    _bootstrap()
    stability = analyze_runtime_stability()
    _render_mapping_table(
        "Runtime Stability",
        [
            ("classification", str(stability.get("classification", "unknown"))),
            ("recurring_convergence_failures", str(stability.get("recurring_convergence_failures", 0))),
            ("repeated_drift_events", str(stability.get("repeated_drift_events", 0))),
            ("unstable_entities", ", ".join(stability.get("unstable_entities", [])) or "none"),
            ("patterns", ", ".join(stability.get("recurring_instability_patterns", [])) or "none"),
        ],
    )


@runtime_app.command("explain-collection")
def runtime_explain_collection() -> None:
    """Explain current collection layer output."""
    config = _bootstrap()
    bundle = collect_runtime_bundle(config, persist=True)
    table = Table(title="NS-DDoS Runtime Collection")
    table.add_column("Area")
    table.add_column("Value")
    table.add_row("schema_version", bundle.schema_version)
    table.add_row("providers", ", ".join(sorted(bundle.provider_status)) or "none")
    table.add_row("flow_count", str(bundle.flow_state.get("flow_count", 0)))
    table.add_row("telemetry_stale", str(bundle.freshness_state.get("stale", False)))
    table.add_row("profile", str(bundle.profile.get("name", "unknown")))
    table.add_row("environment", str(bundle.environment.get("status", "unknown")))
    table.add_row("cache_hit", str(bundle.cache.get("cache_hit", False)))
    console.print(table)
    timing_table = Table(title="Collection Timings")
    timing_table.add_column("Step")
    timing_table.add_column("ms")
    for name, value in sorted(bundle.timings.items()):
        timing_table.add_row(name, f"{float(value):.2f}")
    console.print(timing_table)


@runtime_app.command("explain-analysis")
def runtime_explain_analysis() -> None:
    """Explain analysis layer output from normalized collection."""
    config = _bootstrap()
    aggregation = aggregate_runtime(config, collect_runtime_bundle(config))
    analysis = aggregation.analysis
    _render_mapping_table(
        "Runtime Analysis",
        [
            ("schema_version", analysis.schema_version),
            ("topology_consistent", str(analysis.topology.get("consistent", False))),
            ("convergence", str(analysis.convergence.get("status", "unknown"))),
            ("reconciliation", analysis.reconciliation.get("detail", "")),
            ("drift_items", str(len(analysis.drift))),
            ("stability", str(analysis.temporal.get("stability", {}).get("classification", "unknown"))),
            ("cache_entries", str(cache_summary().get("entries", 0))),
        ],
    )
    timing_table = Table(title="Analysis Timings")
    timing_table.add_column("Step")
    timing_table.add_column("ms")
    timings = {
        **aggregation.performance.get("collection", {}),
        **aggregation.performance.get("analysis", {}),
    }
    for name, value in sorted(timings.items()):
        timing_table.add_row(name, f"{float(value):.2f}")
    console.print(timing_table)


@runtime_app.command("recover-state")
def runtime_recover_state() -> None:
    """Recover runtime state from corruption or schema drift."""
    _bootstrap()
    payload = recover_json(STATE_PATH, RuntimeState().to_dict())
    state = RuntimeState.from_dict(payload)
    write_runtime_state(state)
    _render_mapping_table(
        "Runtime State Recovery",
        [
            ("path", str(STATE_PATH)),
            ("schema_version", state.schema_version),
            ("stack_running", str(state.stack_running)),
            ("topology_state", state.topology_state),
            ("services", str(len(state.services))),
        ],
    )


@runtime_app.command("explain-verification")
def runtime_explain_verification() -> None:
    """Explain authoritative verification pipeline."""
    config = _bootstrap()
    explanation = explain_verification(config)
    execution = explanation["execution"]
    table = Table(title="Runtime Verification Pipeline")
    table.add_column("Validator")
    table.add_column("Order")
    table.add_column("State")
    degraded = set(explanation.get("degraded_validators", []))
    skipped = set(explanation.get("skipped_validators", []))
    for index, validator in enumerate(explanation.get("validator_order", []), start=1):
        state = "skipped" if validator in skipped else ("degraded" if validator in degraded else "ready")
        table.add_row(validator, str(index), state)
    console.print(table)
    category_table = Table(title="Verification Categories")
    category_table.add_column("Category")
    category_table.add_column("Severity")
    category_table.add_column("Results")
    category_table.add_column("Duration ms")
    for category in explanation.get("categories", []):
        category_table.add_row(
            category.get("category", ""),
            category.get("severity", ""),
            str(len(category.get("results", []))),
            f"{float(category.get('duration_ms', 0.0)):.2f}",
        )
    console.print(category_table)
    _render_mapping_table(
        "Verification Summary",
        [
            ("run_id", execution.get("run_id", "")),
            ("severity", execution.get("severity", "unknown")),
            ("evidence", str(len(explanation.get("evidence", [])))),
            ("dependencies", str(len(explanation.get("dependency_graph", [])))),
        ],
    )


@runtime_app.command("replay-verification")
def runtime_replay_verification() -> None:
    """Replay persisted verification runs."""
    _bootstrap()
    replay = replay_verification_runs()
    table = Table(title="Verification Replay")
    table.add_column("Run")
    table.add_column("Severity")
    table.add_column("Results")
    table.add_column("Timestamp")
    for run in replay.get("runs", []):
        table.add_row(
            run.get("run_id", ""),
            run.get("severity", "unknown"),
            str(len(run.get("results", []))),
            run.get("timestamp", ""),
        )
    console.print(table)
    _render_mapping_table(
        "Verification Replay Summary",
        [
            ("runs", str(replay.get("run_count", 0))),
            ("transitions", str(len(replay.get("transitions", [])))),
            ("repeated_failures", ", ".join(sorted(replay.get("repeated_failures", {}))) or "none"),
        ],
    )


@runtime_app.command("explain-query")
def runtime_explain_query() -> None:
    """Explain runtime query architecture."""
    _bootstrap()
    explanation = explain_query_system()
    table = Table(title="Runtime Query Registry")
    table.add_column("Query")
    table.add_column("Scope")
    table.add_column("Dependencies")
    table.add_column("Replay Safe")
    for item in explanation.get("queries", []):
        table.add_row(
            item.get("name", ""),
            item.get("scope", ""),
            ", ".join(item.get("dependencies", [])) or "none",
            str(item.get("replay_safe", False)),
        )
    console.print(table)
    _render_mapping_table(
        "Query Summary",
        [
            ("queries", str(len(explanation.get("queries", [])))),
            ("scopes", str(len(explanation.get("scopes", [])))),
            ("dependencies", str(len(explanation.get("dependencies", [])))),
        ],
    )


@runtime_app.command("query-snapshots")
def runtime_query_snapshots(limit: int = typer.Option(25, "--limit")) -> None:
    """Query runtime snapshots."""
    config = _bootstrap()
    _render_query_result("Runtime Snapshot Query", execute_query(config, _query("snapshots", "persistence", limit)))


@runtime_app.command("query-evidence")
def runtime_query_evidence(limit: int = typer.Option(25, "--limit")) -> None:
    """Query runtime evidence bundles."""
    config = _bootstrap()
    _render_query_result("Runtime Evidence Query", execute_query(config, _query("evidence", "evidence", limit)))


@runtime_app.command("query-verification")
def runtime_query_verification(
    category: str | None = typer.Option(None, "--category"),
    limit: int = typer.Option(25, "--limit"),
) -> None:
    """Query verification registry and replay."""
    config = _bootstrap()
    query = _query("verification", "verification", limit, "category", category) if category else _query("verification", "verification", limit)
    _render_query_result("Runtime Verification Query", execute_query(config, query))


@runtime_app.command("query-timeline")
def runtime_query_timeline(
    status: str | None = typer.Option(None, "--status"),
    limit: int = typer.Option(25, "--limit"),
) -> None:
    """Query runtime timeline events."""
    config = _bootstrap()
    query = _query("timeline", "temporal", limit, "status", status) if status else _query("timeline", "temporal", limit)
    _render_query_result("Runtime Timeline Query", execute_query(config, query))


@runtime_app.command("query-graph")
def runtime_query_graph(
    node_type: str | None = typer.Option(None, "--type"),
    limit: int = typer.Option(25, "--limit"),
) -> None:
    """Query runtime graph."""
    config = _bootstrap()
    query = _query("graph", "graph", limit, "type", node_type) if node_type else _query("graph", "graph", limit)
    _render_query_result("Runtime Graph Query", execute_query(config, query))


@runtime_app.command("query-replay")
def runtime_query_replay(limit: int = typer.Option(25, "--limit")) -> None:
    """Query runtime replay artifacts."""
    config = _bootstrap()
    _render_query_result("Runtime Replay Query", execute_query(config, _query("replay", "replay", limit)))


@api_app.command("routes")
def api_routes() -> None:
    """Show read-only runtime API routes."""
    _bootstrap()
    from nsddos.api.app import get_route_summary

    summary = get_route_summary()
    table = Table(title="NS-DDoS API Routes")
    table.add_column("Path")
    table.add_column("Methods")
    table.add_column("Name")
    table.add_column("Query Backed")
    for route in summary.get("routes", []):
        table.add_row(
            route.get("path", ""),
            ", ".join(route.get("methods", [])),
            route.get("name", ""),
            str(route.get("query_backed", True)),
        )
    console.print(table)
    _render_mapping_table("API Summary", [("routes", str(summary.get("endpoint_count", 0)))])


@api_app.command("explain")
def api_explain() -> None:
    """Explain runtime API architecture."""
    _bootstrap()
    from nsddos.api.app import explain_api

    explanation = explain_api()
    _render_mapping_table(
        "API Architecture",
        [
            ("readonly", str(explanation.get("readonly", False))),
            ("query_backed", str(explanation.get("query_backed", False))),
            ("provider_access", str(explanation.get("provider_access", "unknown"))),
            ("orchestration_access", str(explanation.get("orchestration_access", "unknown"))),
            ("routes", str(explanation.get("route_summary", {}).get("endpoint_count", 0))),
        ],
    )


@api_app.command("start")
def api_start(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int | None = typer.Option(None, "--port"),
) -> None:
    """Start read-only runtime API server."""
    if hasattr(host, "default"):
        host = host.default
    if hasattr(port, "default"):
        port = port.default
    config = _bootstrap()
    api_port = int(port or config.get("api_port", 8008))
    try:
        uvicorn.run("nsddos.api.app:app", host=host, port=api_port, reload=False)
    except KeyboardInterrupt:
        console.print("[yellow]API stopped.[/yellow]")
    except Exception as exc:
        console.print(f"[bold red]API failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@service_app.command("start")
def service_start() -> None:
    """Start runtime coordination service."""
    config = _bootstrap()
    manager = RuntimeServiceManager(config)
    state = manager.start(owner="cli-service")
    _render_mapping_table(
        "Service Start",
        [
            ("state", state.state),
            ("owner", state.owner),
            ("active_session", str(state.active_session_id)),
            ("replay_safe", str(state.replay_safe)),
        ],
    )


@service_app.command("stop")
def service_stop() -> None:
    """Stop runtime coordination service."""
    config = _bootstrap()
    state = RuntimeServiceManager(config).stop()
    _render_mapping_table("Service Stop", [("state", state.state), ("updated_at", str(state.updated_at))])


@service_app.command("status")
def service_status() -> None:
    """Show service status."""
    config = _bootstrap()
    status = RuntimeServiceManager(config).status()
    state = status["state"]
    _render_mapping_table(
        "Service Status",
        [
            ("state", str(state.get("state", "unknown"))),
            ("owner", str(state.get("owner", ""))),
            ("active_session", str(state.get("active_session_id", ""))),
            ("lock_owner", str(status.get("lock_owner", ""))),
            ("degraded", str(state.get("degraded", False))),
        ],
    )


@service_app.command("sessions")
def service_sessions() -> None:
    """Show runtime sessions."""
    config = _bootstrap()
    sessions = RuntimeServiceManager(config).sessions()
    table = Table(title="Service Sessions")
    table.add_column("Session")
    table.add_column("Owner")
    table.add_column("State")
    table.add_column("Lifecycle")
    for item in sessions:
        table.add_row(item.get("session_id", ""), item.get("owner", ""), item.get("state", ""), item.get("lifecycle", ""))
    console.print(table)


@service_app.command("explain")
def service_explain() -> None:
    """Explain service architecture state."""
    config = _bootstrap()
    explanation = RuntimeServiceManager(config).explain()
    _render_mapping_table(
        "Service Explain",
        [
            ("service_state", str(explanation.get("service", {}).get("state", "unknown"))),
            ("daemon_support", str(explanation.get("capabilities", {}).get("daemon_support", False))),
            ("replay_support", str(explanation.get("capabilities", {}).get("replay_support", False))),
            ("subscriptions", str(len(explanation.get("subscriptions", [])))),
        ],
    )


@service_app.command("diagnostics")
def service_diagnostics() -> None:
    """Show service diagnostics."""
    config = _bootstrap()
    diagnostics = RuntimeServiceManager(config).diagnostics()
    _render_mapping_table(
        "Service Diagnostics",
        [
            ("session_count", str(diagnostics.get("session_count", 0))),
            ("heartbeat_count", str(diagnostics.get("heartbeat_count", 0))),
            ("replay_events", str(diagnostics.get("replay", {}).get("event_count", 0))),
            ("sync_state", str(diagnostics.get("synchronization", {}).get("state", "unknown"))),
        ],
    )


@service_app.command("replay")
def service_replay(from_sequence: int = typer.Option(0, "--from-sequence")) -> None:
    """Replay service events."""
    config = _bootstrap()
    replay = RuntimeServiceManager(config).replay(from_sequence=from_sequence)
    _render_mapping_table(
        "Service Replay",
        [
            ("event_count", str(replay.get("event_count", 0))),
            ("from_sequence", str(replay.get("from_sequence", 0))),
            ("latest_sequence", str(replay.get("latest_sequence", 0))),
        ],
    )


@service_app.command("stream-status")
def service_stream_status() -> None:
    """Show stream metadata."""
    config = _bootstrap()
    status = RuntimeServiceManager(config).status()
    streaming = status.get("state", {}).get("streaming", {})
    _render_mapping_table(
        "Service Stream Status",
        [
            ("latest_sequence", str(streaming.get("latest_sequence", 0))),
            ("subscriptions", str(len(streaming.get("subscriptions", [])))),
            ("replay_safe", str(status.get("state", {}).get("replay_safe", True))),
        ],
    )


@ui_app.command("start")
def ui_start(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8010, "--port"),
) -> None:
    """Start operational observability UI server."""
    if hasattr(host, "default"):
        host = host.default
    if hasattr(port, "default"):
        port = port.default
    _bootstrap()
    url = f"http://{host}:{port}/"
    try:
        replace_listener_on_port(port)
        _open_browser(url)

        uvicorn.run("nsddos.ui.app:app", host=host, port=port, reload=False)
    except KeyboardInterrupt:
        console.print("[yellow]UI stopped.[/yellow]")
    except Exception as exc:
        console.print(f"[bold red]UI failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@ui_app.command("explain")
def ui_explain() -> None:
    """Explain UI architecture."""
    _bootstrap()
    from nsddos.ui.app import explain_ui

    explanation = explain_ui()
    _render_mapping_table(
        "UI Explain",
        [
            ("readonly", str(explanation.get("readonly", True))),
            ("query_backed", str(explanation.get("query_backed", True))),
            ("api_only", str(explanation.get("api_only", True))),
            ("replay_safe", str(explanation.get("replay_safe", True))),
            ("surfaces", str(len(explanation.get("surfaces", [])))),
        ],
    )


@ui_app.command("status")
def ui_status() -> None:
    """Show UI status metadata."""
    _bootstrap()
    from nsddos.ui.app import explain_ui

    explanation = explain_ui()
    state = explanation.get("state", {})
    _render_mapping_table(
        "UI Status",
        [
            ("schema_version", str(state.get("schema_version", ""))),
            ("poll_interval_seconds", str(state.get("refresh_metadata", {}).get("poll_interval_seconds", 0))),
            ("deterministic_ordering", str(state.get("refresh_metadata", {}).get("deterministic_ordering", False))),
            ("updated_at", str(state.get("refresh_metadata", {}).get("updated_at", ""))),
        ],
    )


@ui_app.command("expose")
def ui_expose() -> None:
    """Expose local UI through Cloudflare Tunnel."""

    _bootstrap()
    binary = which("cloudflared")
    if binary is None:
        console.print(f"[bold red]cloudflared not found.[/bold red] {_cloudflared_install_hint()}")
        raise typer.Exit(code=1)

    ui_result = launch_ui_background()
    if not ui_result.reachable:
        console.print("[bold red]UI expose failed:[/bold red] local UI not reachable on port 8010.")
        raise typer.Exit(code=1)

    local_url = ui_result.ui_url.rstrip("/")
    console.print(Panel.fit(f"Local UI:   {local_url}\nPublic UI:  waiting for tunnel...", title="NSDDOS UI Expose"))

    process = subprocess.Popen(
        [binary, "tunnel", "--url", local_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    public_url: str | None = None
    try:
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.rstrip()
            if not line:
                continue
            if public_url is None:
                public_url = _parse_trycloudflare_url(line)
                if public_url:
                    console.print(f"Public UI:  {public_url}")
            console.print(line)
        code = process.wait()
    except KeyboardInterrupt:
        process.terminate()
        console.print("[yellow]Cloudflare tunnel stopped.[/yellow]")
        raise typer.Exit(code=130) from None

    if code != 0:
        raise typer.Exit(code=code)


@runtime_app.command("validate-traffic")
def runtime_validate_traffic() -> None:
    """Run safe traffic validation."""
    config = _bootstrap()
    result = validate_traffic(config)
    _render_verification_table("NS-DDoS Traffic Validation", [result])
    if result.status == "fail":
        raise typer.Exit(code=1)


@runtime_app.command("evidence")
def runtime_evidence() -> None:
    """Export runtime evidence bundle."""
    config = _bootstrap()
    bundle = export_evidence_bundle(config)
    console.print(
        Panel.fit(
            f"bundle: {bundle.bundle_dir}\n"
            f"snapshot: {bundle.snapshot_file}\n"
            f"summary: {bundle.summary_file}",
            title="Runtime Evidence",
        )
    )


@runtime_app.command("export-graph")
def runtime_export_graph() -> None:
    """Export runtime graph artifacts."""
    config = _bootstrap()
    artifact = export_runtime_graph(config)
    console.print(
        Panel.fit(
            f"json: {artifact.json_path}\n"
            f"mermaid: {artifact.mermaid_path}\n"
            f"dot: {artifact.dot_path}",
            title="Runtime Graph Export",
        )
    )


@runtime_app.command("export-bundle")
def runtime_export_bundle() -> None:
    """Export portable runtime archive."""
    config = _bootstrap()
    bundle = export_runtime_bundle(config)
    console.print(Panel.fit(str(bundle), title="Runtime Export Bundle"))


@runtime_app.command("export-relationships")
def runtime_export_relationships_cmd() -> None:
    """Export runtime relationships."""
    config = _bootstrap()
    artifact = export_runtime_relationships(config)
    console.print(
        Panel.fit(
            f"json: {artifact['json_path']}\nmermaid: {artifact['mermaid_path']}",
            title="Runtime Relationship Export",
        )
    )


@runtime_app.command("export-history")
def runtime_export_history_cmd() -> None:
    """Export temporal runtime history."""
    config = _bootstrap()
    artifact = export_runtime_history(config)
    console.print(
        Panel.fit(
            f"json: {artifact['json_path']}\nmermaid: {artifact['mermaid_path']}",
            title="Runtime History Export",
        )
    )


@runtime_app.command("explain-pipeline")
def runtime_explain_pipeline() -> None:
    """Explain canonical execution pipeline."""
    config = _bootstrap()
    preset = load_runtime_state().preset_state.get("active", "minimal-lab")
    plan = build_execution_plan(config, preset=preset)
    replay = replay_execution_history()
    table = Table(title="NS-DDoS Runtime Pipeline")
    table.add_column("Phase")
    table.add_column("Dependencies")
    table.add_column("Providers")
    table.add_column("Gate")
    table.add_column("Required")
    for phase in plan.phases:
        table.add_row(
            phase.name,
            ", ".join(phase.dependencies) or "none",
            ", ".join(phase.providers) or "none",
            phase.gate,
            str(phase.required),
        )
    console.print(table)
    _render_mapping_table(
        "Pipeline Replay",
        [
            ("preset", preset),
            ("profile", plan.profile),
            ("events", str(replay.get("event_count", 0))),
            ("warnings", str(len(replay.get("warnings", [])))),
            ("failed", str(len(replay.get("failed", [])))),
        ],
    )


@runtime_app.command("bootstrap")
def runtime_bootstrap(preset: str = typer.Option("minimal-lab", "--preset")) -> None:
    """Run canonical runtime bootstrap pipeline."""
    config = _bootstrap()
    state = execute_pipeline(config, preset=preset, mode="bootstrap")
    _render_mapping_table(
        "Runtime Bootstrap Pipeline",
        [
            ("status", state.status),
            ("preset", state.preset),
            ("profile", state.profile),
            ("phases", str(len(state.results))),
            ("warnings", str(sum(1 for item in state.results if item.status == "warn"))),
        ],
    )


@runtime_app.command("shutdown")
def runtime_shutdown(preset: str = typer.Option("minimal-lab", "--preset")) -> None:
    """Run canonical runtime shutdown pipeline."""
    config = _bootstrap()
    state = shutdown_pipeline(config, preset=preset)
    _render_mapping_table(
        "Runtime Shutdown Pipeline",
        [
            ("status", state.status),
            ("preset", state.preset),
            ("phases", str(len(state.results))),
        ],
    )


@runtime_app.command("export-pipeline")
def runtime_export_pipeline(preset: str = typer.Option("minimal-lab", "--preset")) -> None:
    """Export canonical execution pipeline."""
    config = _bootstrap()
    artifact = export_execution_graph(config, preset=preset)
    console.print(
        Panel.fit(
            f"json: {artifact['json_path']}\nmermaid: {artifact['mermaid_path']}",
            title="Runtime Pipeline Export",
        )
    )


@runtime_app.command("use-preset")
def runtime_use_preset(preset: str = typer.Argument(...)) -> None:
    """Configure active runtime preset."""
    config = _bootstrap()
    state = use_runtime_preset(config, preset)
    _render_mapping_table(
        "Runtime Preset",
        [
            ("active", str(state.get("active", "unknown"))),
            ("expected_topology", str(state.get("preset", {}).get("expected_topology", "unknown"))),
            ("verification_scope", ", ".join(state.get("preset", {}).get("verification_scope", [])) or "none"),
        ],
    )


@runtime_app.command("explain-environment")
def runtime_explain_environment() -> None:
    """Explain runtime environment compatibility."""
    config = _bootstrap()
    profile = detect_runtime_profile()
    capabilities = detect_runtime_capabilities()
    environment = validate_runtime_environment(config)
    reproducibility = analyze_reproducibility(config)

    _render_mapping_table(
        "Runtime Profile",
        [
            ("name", profile.name),
            ("platform", profile.platform),
            ("required_services", ", ".join(profile.required_services) or "none"),
            ("limitations", ", ".join(profile.runtime_limitations) or "none"),
            ("detail", profile.detail),
        ],
    )
    _render_mapping_table(
        "Runtime Capabilities",
        [
            ("docker_daemon", str(capabilities.docker_daemon)),
            ("ovs_service", str(capabilities.ovs_service)),
            ("mininet_supported", str(capabilities.mininet_supported)),
            ("linux_kernel", str(capabilities.linux_kernel)),
            ("sudo_available", str(capabilities.sudo_available)),
            ("passwordless_sudo", str(capabilities.passwordless_sudo)),
            ("wsl2", str(capabilities.wsl2)),
            ("openflow_compatible", str(capabilities.openflow_compatible)),
            ("sflow_capable", str(capabilities.sflow_capable)),
        ],
    )
    _render_mapping_table(
        "Environment Compatibility",
        [
            ("status", environment.status),
            ("supported", ", ".join(environment.supported) or "none"),
            ("degraded", ", ".join(environment.degraded) or "none"),
            ("unsupported", ", ".join(environment.unsupported) or "none"),
            ("missing_deps", ", ".join(environment.missing_dependencies) or "none"),
            ("repro_limits", ", ".join(environment.reproducibility_limitations) or "none"),
            ("reproducibility", reproducibility.status),
        ],
    )


@runtime_app.command("validate-bootstrap")
def runtime_validate_bootstrap() -> None:
    """Validate canonical runtime bootstrap."""
    config = _bootstrap()
    result = validate_bootstrap(config)
    _render_mapping_table(
        "Bootstrap Validation",
        [
            ("profile", str(result.get("profile", "unknown"))),
            ("status", str(result.get("status", "unknown"))),
            ("bootstrap_ready", str(result.get("bootstrap_ready", False))),
            ("missing_dependencies", ", ".join(result.get("missing_dependencies", [])) or "none"),
            ("limitations", ", ".join(result.get("limitations", [])) or "none"),
        ],
    )
    if not result.get("bootstrap_ready"):
        raise typer.Exit(code=1)


@runtime_app.command("install-guide")
def runtime_install_guide() -> None:
    """Show deterministic profile-aware install guidance."""
    _bootstrap()
    profile = detect_runtime_profile()
    guides = {
        "linux-native": [
            "Install Docker Engine + Compose v2.",
            "Install Open vSwitch userland + daemon.",
            "Install Mininet on Linux host.",
            "Enable passwordless sudo for runtime user or run as root.",
            "Validate with: nsddos runtime validate-bootstrap",
        ],
        "docker-linux": [
            "Install Docker Engine + Compose v2.",
            "Build canonical Docker runtime under docker/runtime/base.",
            "Add host OVS + Mininet if full datapath lab needed.",
            "Validate with: nsddos runtime explain-environment",
        ],
        "wsl2": [
            "Use Ubuntu on WSL2.",
            "Enable Docker Desktop WSL integration or native dockerd.",
            "Expect degraded OVS/Mininet unless Linux networking tuned.",
            "Validate with: nsddos runtime validate-bootstrap",
        ],
        "macos-degraded": [
            "Use Docker Desktop for container-only diagnostics.",
            "Do not expect native OVS/Mininet datapath runtime.",
            "Use export/verify/doctor flows only.",
            "Prefer linux-native or docker-linux for canonical lab execution.",
        ],
    }
    _render_mapping_table(
        "Install Guide",
        [(profile.name, step) for step in guides.get(profile.name, ["No guide available."])],
    )


@runtime_app.command("export-environment")
def runtime_export_environment() -> None:
    """Export runtime environment bundle."""
    config = _bootstrap()
    profile = detect_runtime_profile().to_dict()
    capabilities = detect_runtime_capabilities().to_dict()
    environment = validate_runtime_environment(config).to_dict()
    reproducibility = analyze_reproducibility(config).to_dict()
    bootstrap = validate_bootstrap(config)
    from nsddos.constants import RUNTIME_DIR

    bundle_dir = RUNTIME_DIR / "environment"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = bundle_dir / f"runtime-environment-{stamp}.json"
    md_path = bundle_dir / f"runtime-environment-{stamp}.md"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "capabilities": capabilities,
        "environment": environment,
        "reproducibility": reproducibility,
        "bootstrap": bootstrap,
    }
    atomic_write_json(json_path, payload)
    md_path.write_text(
        "\n".join(
            [
                "# NS-DDoS Runtime Environment",
                f"- profile: {profile.get('name', 'unknown')}",
                f"- environment: {environment.get('status', 'unknown')}",
                f"- reproducibility: {reproducibility.get('status', 'unknown')}",
                f"- bootstrap: {bootstrap.get('status', 'unknown')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    console.print(Panel.fit(f"json: {json_path}\nmarkdown: {md_path}", title="Runtime Environment Export"))


@runtime_app.command("explain")
def runtime_explain() -> None:
    """Explain current runtime truth state."""
    config = _bootstrap()
    identity = build_identity_map(config)
    interfaces = correlate_interfaces(config)
    reconciliation = reconcile_runtime(config)

    switch_rows = []
    for item in identity.switches:
        switch_rows.append(
            (
                item.canonical_id,
                f"mininet={item.mininet_name} ovs={item.ovs_bridge} dpid={item.controller_dpid} sflow={item.sflow_agent}",
            )
        )
    _render_mapping_table("Runtime Switch Identity", switch_rows or [("switches", "none")])

    iface_rows = []
    for item in interfaces.interfaces:
        iface_rows.append(
            (
                item.canonical_id,
                f"ovs={item.visible_in_ovs} sflow={item.visible_in_sflow} link={item.mininet_link}",
            )
        )
    _render_mapping_table("Runtime Interface Visibility", iface_rows or [("interfaces", "none")])

    _render_mapping_table(
        "Runtime Reconciliation",
        [
            ("missing", ", ".join(reconciliation.missing_entities) or "none"),
            ("stale", ", ".join(reconciliation.stale_entities) or "none"),
            ("inconsistent", ", ".join(reconciliation.inconsistent_entities) or "none"),
            ("orphan", ", ".join(reconciliation.orphan_entities) or "none"),
            ("reductions", ", ".join(reconciliation.confidence_reductions) or "none"),
        ],
    )


@runtime_app.command("explain-ports")
def runtime_explain_ports() -> None:
    """Explain current datapath port truth."""
    config = _bootstrap()
    openflow = correlate_openflow_ports(config)
    rows = []
    for item in openflow.ports:
        rows.append(
            (
                item.canonical_id,
                f"dpid={item.datapath_id} port={item.port_no} ovs={item.ovs_name} ctrl={item.visible_in_controller} sflow={item.visible_in_sflow}",
            )
        )
    _render_mapping_table("Runtime Datapath Ports", rows or [("ports", "none")])
    _render_mapping_table(
        "Runtime Port Drift",
        [
            ("missing", ", ".join(openflow.missing_ports) or "none"),
            ("stale", ", ".join(openflow.stale_ports) or "none"),
            ("orphan", ", ".join(openflow.orphan_ports) or "none"),
            ("duplicate", ", ".join(openflow.duplicate_ports) or "none"),
        ],
    )


@runtime_app.command("explain-paths")
def runtime_explain_paths() -> None:
    """Explain runtime path truth."""
    config = _bootstrap()
    paths = correlate_paths(config)
    rows = []
    for item in paths.observed_paths:
        rows.append(
            (
                item.canonical_id,
                f"topology={item.visible_in_topology} controller={item.visible_in_controller} telemetry={item.visible_in_telemetry}",
            )
        )
    _render_mapping_table("Runtime Paths", rows or [("paths", "none")])
    _render_mapping_table(
        "Runtime Path Drift",
        [
            ("missing", ", ".join(paths.missing_paths) or "none"),
            ("orphan", ", ".join(paths.orphan_paths) or "none"),
            ("inconsistent", ", ".join(paths.inconsistent_paths) or "none"),
        ],
    )


@runtime_app.command("explain-controller")
def runtime_explain_controller() -> None:
    """Explain authoritative controller truth."""
    config = _bootstrap()
    controller = normalize_controller_topology(config)
    switch_rows = []
    for switch in controller.switches:
        switch_rows.append(
            (
                switch.canonical_id,
                f"dpid={switch.datapath_id} connected={switch.connected} ports={len(switch.ports)}",
            )
        )
    _render_mapping_table("Controller Switches", switch_rows or [("switches", "none")])

    port_rows = []
    for switch in controller.switches:
        for port in switch.ports:
            port_rows.append(
                (
                    f"{switch.canonical_id}:{port.port_no or 'unknown'}",
                    f"name={port.name} state={port.state}",
                )
            )
    _render_mapping_table("Controller Ports", port_rows or [("ports", "none")])
    _render_mapping_table(
        "Controller Drift",
        [
            ("stale_entities", ", ".join(controller.stale_entities) or "none"),
            ("detail", controller.detail),
        ],
    )


@runtime_app.command("explain-convergence")
def runtime_explain_convergence() -> None:
    """Explain runtime convergence state."""
    config = _bootstrap()
    convergence = validate_convergence(config)
    _render_mapping_table(
        "Runtime Convergence",
        [
            ("status", convergence.status),
            ("topology_agreement", str(convergence.topology_agreement)),
            ("datapath_agreement", str(convergence.datapath_agreement)),
            ("controller_agreement", str(convergence.controller_agreement)),
            ("telemetry_agreement", str(convergence.telemetry_agreement)),
            ("divergence_reasons", ", ".join(convergence.divergence_reasons) or "none"),
            ("stale_entities", ", ".join(convergence.stale_entities) or "none"),
        ],
    )


@runtime_app.command("explain-domain")
def runtime_explain_domain() -> None:
    """Explain typed runtime domain architecture."""
    _bootstrap()
    registry = default_domain_registry()
    _render_mapping_table(
        "Runtime Domain Contracts",
        [
            ("entity_types", str(len(registry.entity_types))),
            ("relationship_types", str(len(registry.relationship_types))),
            ("contract_versions", str(len(registry.contract_versions))),
            ("schema_version", "1.0"),
            ("contract_version", "17.0"),
        ],
    )


@runtime_app.command("validate-contracts")
def runtime_validate_contracts() -> None:
    """Validate domain contract integrity."""
    config = _bootstrap()
    graph = build_runtime_graph(config)
    contract_errors = validate_contract_payload({"schema_version": "1.0", "contract_version": "17.0"})
    entity_ids = {str(node.get("id", "")) for node in graph.get("nodes", [])}
    relationship_errors = validate_relationship_integrity(
        [
            {
                "source_id": edge.get("source", ""),
                "target_id": edge.get("target", ""),
                "relationship_type": edge.get("type", ""),
            }
            for edge in graph.get("edges", [])
        ],
        entity_ids,
    )
    stable = validate_identifier_stability("runtime-domain", "runtime-domain")
    _render_mapping_table(
        "Contract Validation",
        [
            ("contract_errors", str(len(contract_errors))),
            ("relationship_errors", str(len(relationship_errors))),
            ("identifier_stability", str(stable)),
        ],
    )
    if contract_errors or relationship_errors or not stable:
        raise typer.Exit(code=1)


@runtime_app.command("validate-replay")
def runtime_validate_replay() -> None:
    """Validate replay contract compatibility."""
    _bootstrap()
    replay = replay_execution_history()
    _render_mapping_table(
        "Replay Validation",
        [
            ("event_count", str(replay.get("event_count", 0))),
            ("typed_events", str(len(replay.get("typed_replay", [])))),
            ("contract_errors", str(len(replay.get("replay_contract_errors", [])))),
        ],
    )
    if replay.get("replay_contract_errors"):
        raise typer.Exit(code=1)


@runtime_app.command("explain-producers")
def runtime_explain_producers() -> None:
    """Explain typed producer architecture."""
    _bootstrap()
    registry = default_producer_registry()
    table = Table(title="Runtime Producers")
    table.add_column("Producer")
    table.add_column("Entity Contract")
    table.add_column("Dependencies")
    table.add_column("Replay Compatible")
    for definition in registry.ordered():
        table.add_row(
            definition.name,
            definition.entity_contract,
            ", ".join(definition.dependencies) or "none",
            str(definition.replay_compatible),
        )
    console.print(table)


@runtime_app.command("validate-producers")
def runtime_validate_producers() -> None:
    """Validate producer determinism and contract integrity."""
    _bootstrap()
    registry = default_producer_registry()
    failures: list[str] = []
    for definition in registry.ordered():
        output = produce_records(definition.name, [{"id": f"{definition.name}-sample", "type": definition.entity_contract.lower()}])
        if len(output.entities) != 1:
            failures.append(f"{definition.name}:empty")
            continue
        payload = output.entities[0].record.to_dict()
        errors = validate_contract_payload(payload)
        if errors:
            failures.append(f"{definition.name}:{','.join(errors)}")
    _render_mapping_table(
        "Producer Validation",
        [
            ("producer_count", str(len(registry.producers))),
            ("failures", str(len(failures))),
            ("valid", str(not failures)),
        ],
    )
    if failures:
        raise typer.Exit(code=1)


@runtime_app.command("replay-producers")
def runtime_replay_producers() -> None:
    """Replay producer-compatible runtime events."""
    _bootstrap()
    replay = replay_execution_history()
    events = replay.get("phases", [])
    output = produce_records("replay", events)
    _render_mapping_table(
        "Producer Replay",
        [
            ("runtime_events", str(len(events))),
            ("typed_entities", str(len(output.entities))),
            ("replay_errors", str(len(replay.get("replay_contract_errors", [])))),
        ],
    )
    if replay.get("replay_contract_errors"):
        raise typer.Exit(code=1)


@runtime_app.command("producer-lineage")
def runtime_producer_lineage() -> None:
    """Show producer dependency lineage."""
    _bootstrap()
    registry = default_producer_registry()
    table = Table(title="Producer Lineage")
    table.add_column("Producer")
    table.add_column("Depends On")
    for definition in registry.ordered():
        table.add_row(definition.name, ", ".join(definition.dependencies) or "root")
    console.print(table)


@runtime_app.command("explain-freshness")
def runtime_explain_freshness() -> None:
    """Explain runtime freshness model."""
    _bootstrap()
    detail = explain_freshness()
    _render_mapping_table(
        "Runtime Freshness",
        [
            ("schema", str(detail["metadata"]["schema"])),
            ("contract", str(detail["metadata"]["contract"])),
            ("temporal_guarantee", str(detail["metadata"]["temporal_guarantee"])),
            ("windows", str(len(detail["thresholds"]))),
            ("validity_states", ", ".join(detail["states"])),
        ],
    )


@runtime_app.command("validate-freshness")
def runtime_validate_freshness() -> None:
    """Validate freshness contracts and temporal consistency."""
    config = _bootstrap()
    graph = build_runtime_graph(config)
    sample = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "synchronized_at": datetime.now(timezone.utc).isoformat(),
        "freshness_window": "graph",
        "freshness_status": "authoritative-live",
        "validity_state": "valid",
        "replay_validity": "replay-safe",
        "consistency_generation": "probe",
    }
    errors = validate_freshness_payload(sample)
    consistency = validate_consistency("graph", graph)
    _render_mapping_table(
        "Freshness Validation",
        [
            ("contract_errors", str(len(errors))),
            ("consistency_valid", str(consistency.valid)),
            ("consistency_generation", consistency.generation),
            ("consistency_issues", ", ".join(consistency.issues) or "none"),
        ],
    )
    if errors:
        raise typer.Exit(code=1)


@runtime_app.command("explain-consistency")
def runtime_explain_consistency() -> None:
    """Explain runtime consistency generation."""
    config = _bootstrap()
    graph = build_runtime_graph(config)
    consistency = validate_consistency("graph", graph)
    _render_mapping_table(
        "Runtime Consistency",
        [
            ("scope", consistency.scope),
            ("valid", str(consistency.valid)),
            ("generation", consistency.generation),
            ("issues", ", ".join(consistency.issues) or "none"),
        ],
    )


@runtime_app.command("replay-consistency")
def runtime_replay_consistency() -> None:
    """Validate replay consistency and freshness."""
    _bootstrap()
    replay = replay_execution_history()
    events = replay.get("typed_replay", [])
    statuses = [validate_replay_freshness(item) for item in events]
    inconsistent = [item for item in statuses if item.get("validity_state") in {"expired", "inconsistent"}]
    _render_mapping_table(
        "Replay Consistency",
        [
            ("events", str(len(events))),
            ("inconsistent", str(len(inconsistent))),
            ("replay_errors", str(len(replay.get("replay_contract_errors", [])))),
        ],
    )
    if replay.get("replay_contract_errors"):
        raise typer.Exit(code=1)


@runtime_app.command("freshness-lineage")
def runtime_freshness_lineage() -> None:
    """Explain freshness inheritance propagation."""
    _bootstrap()
    cases = (
        ("stale", "valid"),
        ("expired", "valid"),
        ("inconsistent", "stale"),
        ("valid", "valid"),
    )
    table = Table(title="Freshness Lineage")
    table.add_column("Parent")
    table.add_column("Child")
    table.add_column("Inherited")
    for parent_state, child_state in cases:
        table.add_row(parent_state, child_state, propagate_state(parent_state, child_state))
    console.print(table)


@runtime_app.command("detect")
def runtime_detect() -> None:
    """Evaluate detection state."""
    config = _bootstrap()
    evaluation = evaluate_detection(config)
    _render_mapping_table(
        "Runtime Detection",
        [
            ("attack_detected", str(evaluation.attack_detected)),
            ("attack_type", evaluation.attack_type),
            ("confidence_score", f"{evaluation.confidence_score:.4f}"),
            ("risk_level", evaluation.risk_level),
            ("detection_status", evaluation.detection_status),
            ("evidence_hash", evaluation.evidence_hash),
        ],
    )


@runtime_app.command("explain-detection")
def runtime_explain_detection() -> None:
    """Explain detection registry and thresholds."""
    _bootstrap()
    detail = explain_detection()
    _render_mapping_table(
        "Detection Explain",
        [
            ("attacks", str(len(detail.get("attacks", [])))),
            ("anomalies", str(len(detail.get("anomalies", [])))),
            ("features", str(len(detail.get("features", [])))),
            ("baseline_source", str(detail.get("baseline_source", "fallback"))),
            ("score_weights", json.dumps(detail.get("score_weights", {}), sort_keys=True)),
        ],
    )


@runtime_app.command("validate-detection")
def runtime_validate_detection() -> None:
    """Validate detection evaluation and contracts."""
    config = _bootstrap()
    evaluation = evaluate_detection(config)
    errors = validate_detection_evaluation(evaluation)
    _render_mapping_table(
        "Detection Validation",
        [
            ("errors", str(len(errors))),
            ("attack_type", evaluation.attack_type),
            ("risk_level", evaluation.risk_level),
            ("confidence_score", f"{evaluation.confidence_score:.4f}"),
        ],
    )
    if errors:
        raise typer.Exit(code=1)


@runtime_app.command("detection-evidence")
def runtime_detection_evidence() -> None:
    """Show latest detection evidence."""
    config = _bootstrap()
    evidence = latest_detection_evidence()
    if not evidence:
        evidence = evaluate_detection(config).to_dict()
    _render_mapping_table(
        "Detection Evidence",
        [
            ("evidence_hash", str(evidence.get("evidence_hash", ""))),
            ("classification_generation", str(evidence.get("classification_generation", ""))),
            ("provider_source", str(evidence.get("evidence", {}).get("provider_source", evidence.get("provider_source", "")))),
            ("telemetry_timestamp", str(evidence.get("telemetry_timestamp", ""))),
        ],
    )


@runtime_app.command("mitigate")
def runtime_mitigate() -> None:
    """Evaluate mitigation state."""
    config = _bootstrap()
    evaluation = evaluate_mitigation(config)
    _render_mapping_table(
        "Runtime Mitigation",
        [
            ("mitigation_required", str(evaluation.mitigation_required)),
            ("mitigation_action", evaluation.mitigation_action),
            ("target_ip", evaluation.target_ip or "n/a"),
            ("mitigation_status", evaluation.mitigation_status),
            ("execution_result", evaluation.execution_result),
            ("mitigation_hash", evaluation.mitigation_hash),
        ],
    )


@runtime_app.command("enforce-mitigation")
def runtime_enforce_mitigation() -> None:
    """Evaluate and enforce mitigation state."""
    config = _bootstrap()
    evaluation = enforce_mitigation(config, evaluate_mitigation(config))
    _render_mapping_table(
        "Runtime Mitigation Enforcement",
        [
            ("mitigation_action", evaluation.mitigation_action),
            ("target_ip", evaluation.target_ip or "n/a"),
            ("mitigation_status", evaluation.mitigation_status),
            ("execution_result", evaluation.execution_result),
            ("controller_mutation_status", evaluation.controller_mutation_status),
            ("ovs_insertion_status", evaluation.ovs_insertion_status),
            ("flow_verification_status", evaluation.flow_verification_status),
            ("traffic_block_status", evaluation.traffic_block_status),
        ],
    )


@runtime_app.command("explain-mitigation")
def runtime_explain_mitigation() -> None:
    """Explain mitigation registry and actions."""
    _bootstrap()
    detail = explain_mitigation()
    _render_mapping_table(
        "Mitigation Explain",
        [
            ("actions", str(len(detail.get("actions", [])))),
            ("policies", str(len(detail.get("policies", [])))),
            ("strategies", str(len(detail.get("strategies", [])))),
            ("target_selection", str(detail.get("target_selection", ""))),
            ("controller_mode", str(detail.get("controller_mode", ""))),
        ],
    )


@runtime_app.command("validate-mitigation")
def runtime_validate_mitigation() -> None:
    """Validate mitigation evaluation and contracts."""
    config = _bootstrap()
    evaluation = evaluate_mitigation(config)
    errors = validate_mitigation_evaluation(evaluation)
    _render_mapping_table(
        "Mitigation Validation",
        [
            ("errors", str(len(errors))),
            ("mitigation_action", evaluation.mitigation_action),
            ("target_ip", evaluation.target_ip or "n/a"),
            ("confidence_score", f"{evaluation.confidence_score:.4f}"),
        ],
    )
    if errors:
        raise typer.Exit(code=1)


@runtime_app.command("mitigation-evidence")
def runtime_mitigation_evidence() -> None:
    """Show latest mitigation evidence."""
    config = _bootstrap()
    evidence = latest_mitigation_evidence()
    if not evidence:
        evidence = evaluate_mitigation(config).to_dict()
    _render_mapping_table(
        "Mitigation Evidence",
        [
            ("mitigation_hash", str(evidence.get("mitigation_hash", ""))),
            ("mitigation_generation", str(evidence.get("mitigation_generation", ""))),
            ("mitigation_action", str(evidence.get("mitigation_action", ""))),
            ("target_ip", str(evidence.get("target_ip", ""))),
        ],
    )


@runtime_app.command("collect-live")
def runtime_collect_live() -> None:
    """Collect live provider telemetry."""
    config = _bootstrap()
    snapshot = collect_live_telemetry(config)
    _render_mapping_table(
        "Live Telemetry",
        [
            ("provider_source", snapshot.provider_source),
            ("packet_rate", f"{snapshot.packet_rate:.2f}"),
            ("byte_rate", f"{snapshot.byte_rate:.2f}"),
            ("active_flows", str(snapshot.active_flows)),
            ("health_state", snapshot.health_state),
            ("controller_status", snapshot.controller_status),
        ],
    )


@runtime_app.command("provider-health")
def runtime_provider_health() -> None:
    """Show live provider health."""
    config = _bootstrap()
    snapshot = collect_live_telemetry(config)
    health = collect_provider_health(snapshot.provider_health)
    rows = []
    for name, item in sorted(health.items()):
        rows.append((name, f"{item['state']} reachable={item['reachable']} latency_ms={item['latency_ms']:.2f}"))
    _render_mapping_table("Provider Health", rows)


@runtime_app.command("provider-discovery")
def runtime_provider_discovery() -> None:
    """Show live provider discovery."""
    config = _bootstrap()
    snapshot = collect_live_telemetry(config)
    discovery = discover_runtime_providers(
        floodlight_switches=tuple(snapshot.topology_state.switches),
        mininet_switches=tuple(snapshot.topology_state.switches),
        mininet_hosts=tuple(snapshot.topology_state.hosts),
        controller_endpoint=snapshot.topology_state.controllers[0] if snapshot.topology_state.controllers else "",
    )
    rows = []
    for item in discovery:
        payload = item.to_dict()
        rows.append((item.provider, f"switches={len(payload['switches'])} hosts={len(payload['hosts'])} controllers={len(payload['controllers'])}"))
    _render_mapping_table("Provider Discovery", rows)


@runtime_app.command("provider-diagnostics")
def runtime_provider_diagnostics() -> None:
    """Show live provider diagnostics."""
    config = _bootstrap()
    diagnostics = build_provider_diagnostics(collect_live_telemetry(config))
    rows = []
    for item in diagnostics:
        rows.append((item.provider, f"state={item.health_state} latency_ms={item.latency_ms:.2f} anomalies={','.join(item.anomalies) or 'none'}"))
    _render_mapping_table("Provider Diagnostics", rows)


@runtime_app.command("attack-live")
def runtime_attack_live(
    attack: str = typer.Option("all", "--attack"),
    attacker: str = typer.Option("h1", "--attacker"),
    victim: str = typer.Option("h2", "--victim"),
    probe: str = typer.Option("h3", "--probe"),
    target_ip: str = typer.Option("10.0.0.2", "--target-ip"),
    target_port: int = typer.Option(8081, "--target-port"),
    warmup: int = typer.Option(10, "--warmup"),
    attack_seconds: int = typer.Option(15, "--attack-seconds"),
    cooldown: int = typer.Option(15, "--cooldown"),
) -> None:
    """Execute live Mininet attack suite."""
    config = _bootstrap()
    report = run_live_attack_suite(
        config,
        attack=attack,
        attacker=attacker,
        victim=victim,
        probe=probe,
        target_ip=target_ip,
        target_port=target_port,
        warmup=warmup,
        attack_seconds=attack_seconds,
        cooldown=cooldown,
    )
    _render_mapping_table(
        "Live Attack Suite",
        [
            ("run_id", str(report.get("run_id", ""))),
            ("scenarios", str(len(report.get("scenarios", [])))),
            ("report_path", str(report.get("report_path", ""))),
        ],
    )


@runtime_app.command("simulate")
def runtime_simulate() -> None:
    """Generate deterministic attack traffic contract."""
    config = _bootstrap()
    contract = generate_attack_traffic(config)
    _render_mapping_table(
        "Simulation",
        [
            ("attack_type", contract.attack_type),
            ("target_ip", contract.target_ip),
            ("packet_rate", f"{contract.packet_rate:.2f}"),
            ("byte_rate", f"{contract.byte_rate:.2f}"),
            ("duration_seconds", str(contract.duration_seconds)),
            ("intensity_level", contract.intensity_level),
        ],
    )


@runtime_app.command("simulate-replay")
def runtime_simulate_replay() -> None:
    """Generate deterministic replay simulation contract."""
    config = _bootstrap()
    contract = generate_attack_traffic(config, replay_mode=True)
    _render_mapping_table(
        "Simulation Replay",
        [
            ("attack_type", contract.attack_type),
            ("target_ip", contract.target_ip),
            ("replay_records", str(len(contract.replay_records))),
            ("duration_seconds", str(contract.duration_seconds)),
        ],
    )


@runtime_app.command("simulation-diagnostics")
def runtime_simulation_diagnostics() -> None:
    """Show simulation diagnostics."""
    config = _bootstrap()
    diagnostics = build_simulation_diagnostics(generate_attack_traffic(config, replay_mode=True))
    _render_mapping_table(
        "Simulation Diagnostics",
        [
            ("packet_count", str(diagnostics.packet_count)),
            ("byte_count", str(diagnostics.byte_count)),
            ("schedule_duration_ms", str(diagnostics.schedule_duration_ms)),
            ("replay_drift_detected", str(diagnostics.replay_drift_detected)),
        ],
    )


@runtime_app.command("simulation-topology")
def runtime_simulation_topology() -> None:
    """Show simulation topology routing."""
    config = _bootstrap()
    contract = generate_attack_traffic(config)
    _render_mapping_table(
        "Simulation Topology",
        [
            ("attack_type", contract.attack_type),
            ("target_ip", contract.target_ip),
            ("topology_path", " -> ".join(contract.topology_path)),
        ],
    )


@runtime_app.command("stream-start")
def runtime_stream_start() -> None:
    """Process bounded streaming batch."""
    config = _bootstrap()
    evaluation = process_stream_events(config)
    _render_mapping_table(
        "Streaming",
        [
            ("session_id", evaluation.session.session_id),
            ("active_events", str(evaluation.active_events)),
            ("queue_depth", str(evaluation.queue_state.queue_depth)),
            ("dropped_events", str(evaluation.dropped_events)),
            ("throughput", f"{evaluation.throughput:.2f}"),
            ("stream_state", evaluation.stream_state),
        ],
    )


@runtime_app.command("stream-status")
def runtime_stream_status() -> None:
    """Show latest stream status."""
    config = _bootstrap()
    payload = latest_streaming_evaluation() or process_stream_events(config).to_dict()
    _render_mapping_table(
        "Streaming Status",
        [
            ("session_id", str(payload.get("session", {}).get("session_id", ""))),
            ("active_events", str(payload.get("active_events", 0))),
            ("queue_depth", str(payload.get("queue_state", {}).get("queue_depth", 0))),
            ("dropped_events", str(payload.get("dropped_events", 0))),
            ("throughput", f"{float(payload.get('throughput', 0.0)):.2f}"),
            ("stream_state", str(payload.get("stream_state", "unknown"))),
        ],
    )


@runtime_app.command("stream-checkpoint")
def runtime_stream_checkpoint() -> None:
    """Show latest stream checkpoint."""
    config = _bootstrap()
    payload = latest_checkpoint() or process_stream_events(config).checkpoint.to_dict()
    _render_mapping_table(
        "Streaming Checkpoint",
        [
            ("session_id", str(payload.get("session_id", ""))),
            ("checkpoint_id", str(payload.get("checkpoint_id", ""))),
            ("event_offset", str(payload.get("event_offset", 0))),
            ("sequence_number", str(payload.get("sequence_number", 0))),
            ("queue_depth", str(payload.get("queue_state", {}).get("queue_depth", 0))),
        ],
    )


@runtime_app.command("stream-diagnostics")
def runtime_stream_diagnostics() -> None:
    """Show latest stream diagnostics."""
    config = _bootstrap()
    payload = latest_streaming_evaluation() or process_stream_events(config).to_dict()
    diagnostics = payload.get("diagnostics", {})
    _render_mapping_table(
        "Streaming Diagnostics",
        [
            ("queue_latency_ms", f"{float(diagnostics.get('queue_latency_ms', 0.0)):.2f}"),
            ("processing_throughput", f"{float(diagnostics.get('processing_throughput', 0.0)):.2f}"),
            ("dropped_event_count", str(diagnostics.get("dropped_event_count", 0))),
            ("buffer_pressure", f"{float(diagnostics.get('buffer_pressure', 0.0)):.2f}"),
            ("session_health", str(diagnostics.get("session_health", "unknown"))),
            ("checkpoint_lag", str(diagnostics.get("checkpoint_lag", 0))),
        ],
    )


@runtime_app.command("policy-evaluate")
def runtime_policy_evaluate() -> None:
    """Evaluate dynamic policy."""
    config = _bootstrap()
    evaluation = evaluate_dynamic_policy(config)
    _render_mapping_table(
        "Dynamic Policy",
        [
            ("policy_id", evaluation.policy_id),
            ("recommended_action", evaluation.recommended_action),
            ("escalation_level", str(evaluation.escalation_level)),
            ("threshold_score", f"{evaluation.threshold_score:.4f}"),
            ("attack_frequency", str(evaluation.attack_frequency)),
            ("timestamp", evaluation.timestamp.isoformat()),
        ],
    )


@runtime_app.command("policy-history")
def runtime_policy_history() -> None:
    """Show policy history."""
    _bootstrap()
    payload = latest_history_payload()
    rows = []
    for item in payload.get("entries", []):
        rows.append((str(item.get("policy_id", "")), f"{item.get('recommended_action', 'alert_only')} escalation={item.get('escalation_level', 0)}"))
    _render_mapping_table("Policy History", rows or [("entries", "none")])


@runtime_app.command("policy-diagnostics")
def runtime_policy_diagnostics() -> None:
    """Show latest policy diagnostics."""
    config = _bootstrap()
    payload = latest_policy_evaluation() or evaluate_dynamic_policy(config).to_dict()
    diagnostics = payload.get("diagnostics", {})
    _render_mapping_table(
        "Policy Diagnostics",
        [
            ("decision_latency_ms", f"{float(diagnostics.get('decision_latency_ms', 0.0)):.2f}"),
            ("conflict_count", str(diagnostics.get("conflict_count", 0))),
            ("escalation_level", str(diagnostics.get("escalation_level", 0))),
            ("rollback_ready", str(diagnostics.get("rollback_ready", False))),
            ("threshold_drift", f"{float(diagnostics.get('threshold_drift', 0.0)):.4f}"),
        ],
    )


@runtime_app.command("policy-rollback")
def runtime_policy_rollback() -> None:
    """Rollback policy state."""
    config = _bootstrap()
    rollback = rollback_dynamic_policy(config)
    _render_mapping_table(
        "Policy Rollback",
        [
            ("restored_policy_id", rollback.restored_policy_id),
            ("restored_action", rollback.restored_action),
            ("restored_escalation_level", str(rollback.restored_escalation_level)),
            ("restored_threshold_score", f"{rollback.restored_threshold_score:.4f}"),
            ("restored", str(rollback.restored)),
        ],
    )


@runtime_app.command("ml-train")
def runtime_ml_train() -> None:
    """Train deterministic ML model."""
    config = _bootstrap()
    evaluation = train_ml_model(config)
    _render_mapping_table(
        "ML Train",
        [
            ("model_id", evaluation.model_id),
            ("model_version", evaluation.model_version),
            ("attack_probability", f"{evaluation.attack_probability:.4f}"),
            ("predicted_attack_type", evaluation.predicted_attack_type),
            ("retraining_required", str(evaluation.retraining_required)),
        ],
    )


@runtime_app.command("ml-infer")
def runtime_ml_infer() -> None:
    """Run deterministic ML inference."""
    config = _bootstrap()
    evaluation = evaluate_ml_detection(config)
    _render_mapping_table(
        "ML Infer",
        [
            ("model_id", evaluation.model_id),
            ("attack_probability", f"{evaluation.attack_probability:.4f}"),
            ("predicted_attack_type", evaluation.predicted_attack_type),
            ("confidence_score", f"{evaluation.confidence_score:.4f}"),
            ("anomaly_score", f"{evaluation.anomaly_score:.4f}"),
            ("drift_score", f"{evaluation.drift_score:.4f}"),
        ],
    )


@runtime_app.command("ml-diagnostics")
def runtime_ml_diagnostics() -> None:
    """Show ML diagnostics."""
    config = _bootstrap()
    payload = latest_ml_evaluation() or evaluate_ml_detection(config).to_dict()
    diagnostics = payload.get("diagnostics", {})
    metrics = diagnostics.get("model_accuracy_metrics", {})
    drift = diagnostics.get("drift_metrics", {})
    _render_mapping_table(
        "ML Diagnostics",
        [
            ("precision", f"{float(metrics.get('precision', 0.0)):.4f}"),
            ("recall", f"{float(metrics.get('recall', 0.0)):.4f}"),
            ("false_positive_rate", f"{float(metrics.get('false_positive_rate', 0.0)):.4f}"),
            ("confidence_quality", f"{float(metrics.get('confidence_quality', 0.0)):.4f}"),
            ("drift_score", f"{float(drift.get('drift_score', 0.0)):.4f}"),
            ("retraining_frequency", str(diagnostics.get("retraining_frequency", 0))),
        ],
    )


@runtime_app.command("ml-retrain")
def runtime_ml_retrain() -> None:
    """Retrain deterministic ML model."""
    config = _bootstrap()
    evaluation = retrain_ml_model(config)
    _render_mapping_table(
        "ML Retrain",
        [
            ("model_id", evaluation.model_id),
            ("model_version", evaluation.model_version),
            ("attack_probability", f"{evaluation.attack_probability:.4f}"),
            ("drift_score", f"{evaluation.drift_score:.4f}"),
            ("retraining_required", str(evaluation.retraining_required)),
        ],
    )


@app.command("deploy")
def deploy() -> None:
    """Compute dry-run deployment evaluation."""
    config = _bootstrap()
    evaluation = deploy_runtime_stack(config)
    _render_mapping_table(
        "Deployment",
        [
            ("deployment_id", evaluation.deployment_id),
            ("environment", evaluation.environment),
            ("container_count", str(len(evaluation.container_contracts))),
            ("service_health", evaluation.health.service_health),
            ("deployment_state", evaluation.deployment_state),
            ("rollback_available", str(evaluation.rollback_state.rollback_available)),
        ],
    )


@app.command("deployment-health")
def deployment_health_command() -> None:
    """Show deployment health summary."""
    config = _bootstrap()
    evaluation = deployment_health(config)
    _render_mapping_table(
        "Deployment Health",
        [
            ("deployment_id", evaluation.deployment_id),
            ("environment", evaluation.environment),
            ("health_state", evaluation.health.state),
            ("service_health", evaluation.health.service_health),
            ("environment_ready", str(evaluation.health.environment_ready)),
            ("deployment_state", evaluation.deployment_state),
        ],
    )


@app.command("deployment-diagnostics")
def deployment_diagnostics_command() -> None:
    """Show deployment diagnostics."""
    config = _bootstrap()
    evaluation = deployment_health(config)
    _render_mapping_table("Deployment Diagnostics", diagnostics_to_rows(evaluation.diagnostics))


@app.command("deployment-rollback")
def deployment_rollback_command() -> None:
    """Compute dry-run rollback plan."""
    config = _bootstrap()
    evaluation = rollback_runtime_stack(config)
    _render_mapping_table(
        "Deployment Rollback",
        [
            ("deployment_id", evaluation.deployment_id),
            ("rollback_id", evaluation.rollback_state.rollback_id),
            ("target_version", evaluation.rollback_state.target_version),
            ("rollback_available", str(evaluation.rollback_state.rollback_available)),
            ("deployment_state", evaluation.deployment_state),
        ],
    )


@app.command("distributed-orchestrate")
def distributed_orchestrate_command() -> None:
    """Compute dry-run distributed orchestration."""
    config = _bootstrap()
    evaluation = orchestrate_cluster_runtime(config)
    _render_mapping_table(
        "Distributed Runtime",
        [
            ("cluster_id", evaluation.cluster_id),
            ("active_nodes", str(evaluation.active_nodes)),
            ("leader_node", evaluation.leader_node),
            ("worker_count", str(evaluation.worker_count)),
            ("replication_factor", str(evaluation.replication_factor)),
            ("partition_count", str(evaluation.partition_count)),
            ("cluster_health", evaluation.cluster_health),
            ("checkpoint_state", evaluation.checkpoint_state),
        ],
    )


@app.command("distributed-health")
def distributed_health_command() -> None:
    """Show distributed health summary."""
    config = _bootstrap()
    evaluation = distributed_health(config)
    _render_mapping_table(
        "Distributed Health",
        [
            ("cluster_id", evaluation.cluster_id),
            ("active_nodes", str(evaluation.active_nodes)),
            ("leader_node", evaluation.leader_node),
            ("cluster_health", evaluation.cluster_health),
            ("failover_available", str(evaluation.failover_available)),
            ("checkpoint_state", evaluation.checkpoint_state),
        ],
    )


@app.command("distributed-diagnostics")
def distributed_diagnostics_command() -> None:
    """Show distributed diagnostics."""
    config = _bootstrap()
    evaluation = distributed_health(config)
    _render_mapping_table("Distributed Diagnostics", distributed_diagnostics_to_rows(evaluation.diagnostics))


@app.command("distributed-failover")
def distributed_failover_command() -> None:
    """Show distributed failover plan."""
    config = _bootstrap()
    evaluation = distributed_health(config)
    failover = distributed_failover_plan(config)
    _render_mapping_table(
        "Distributed Failover",
        [
            ("cluster_id", evaluation.cluster_id),
            ("leader_failover_node", failover.leader_failover_node or "n/a"),
            ("failover_available", str(failover.failover_available)),
            ("failed_nodes", ",".join(failover.failed_nodes) or "none"),
            ("reassigned_workers", ",".join(failover.reassigned_workers) or "none"),
            ("recovery_state", failover.recovery_state),
        ],
    )


@app.command("dashboard")
def dashboard_command() -> None:
    """Show dashboard summary."""
    config = _bootstrap()
    evaluation = generate_dashboard_state(config)
    _render_mapping_table(
        "Dashboard",
        [
            ("dashboard_id", evaluation.dashboard_id),
            ("active_attacks", str(evaluation.active_attacks)),
            ("active_alerts", str(evaluation.active_alerts)),
            ("stream_throughput", f"{evaluation.stream_throughput:.2f}"),
            ("cluster_nodes", str(evaluation.cluster_nodes)),
            ("ml_confidence", f"{evaluation.ml_confidence:.4f}"),
            ("mitigation_events", str(evaluation.mitigation_events)),
            ("policy_events", str(evaluation.policy_events)),
            ("dashboard_health", evaluation.dashboard_health),
        ],
    )


@app.command("dashboard-alerts")
def dashboard_alerts_command() -> None:
    """Show dashboard alerts."""
    config = _bootstrap()
    alerts = dashboard_alerts(config)
    rows = [(item["alert_id"], f"{item['level']} {item['alert_type']} {item['message']}") for item in alerts]
    _render_mapping_table("Dashboard Alerts", rows or [("alerts", "none")])


@app.command("dashboard-report")
def dashboard_report_command() -> None:
    """Show dashboard reports."""
    config = _bootstrap()
    reports = dashboard_report(config)
    rows = [(item["report_id"], f"{item['report_type']} {item['summary']}") for item in reports]
    _render_mapping_table("Dashboard Reports", rows or [("reports", "none")])


@app.command("dashboard-diagnostics")
def dashboard_diagnostics_command() -> None:
    """Show dashboard diagnostics."""
    config = _bootstrap()
    diagnostics = dashboard_diagnostics(config)
    _render_mapping_table(
        "Dashboard Diagnostics",
        [
            ("dashboard_latency_ms", f"{float(diagnostics.get('dashboard_latency_ms', 0.0)):.2f}"),
            ("visualization_errors", ",".join(diagnostics.get("visualization_errors", [])) or "none"),
            ("stale_telemetry_warnings", ",".join(diagnostics.get("stale_telemetry_warnings", [])) or "none"),
            ("missing_data_warnings", ",".join(diagnostics.get("missing_data_warnings", [])) or "none"),
        ],
    )


@app.command("release-build")
def release_build_command() -> None:
    """Compute deterministic release candidate."""
    config = _bootstrap()
    evaluation = generate_release_candidate(config)
    errors = validate_release_candidate(evaluation)
    _render_mapping_table(
        "Release Build",
        [
            ("release_id", evaluation.release_id),
            ("release_version", evaluation.release_version),
            ("benchmark_score", f"{evaluation.benchmark_score:.4f}"),
            ("load_test_score", f"{evaluation.load_test_score:.4f}"),
            ("stress_test_score", f"{evaluation.stress_test_score:.4f}"),
            ("security_score", f"{evaluation.security_score:.4f}"),
            ("dependency_health", evaluation.dependency_health),
            ("performance_score", f"{evaluation.performance_score:.4f}"),
            ("hardening_state", evaluation.hardening_state),
            ("compliance_state", evaluation.compliance_state),
            ("release_state", evaluation.release_state),
        ],
    )
    if errors or evaluation.release_state == "release_blocked":
        raise typer.Exit(code=1)


@app.command("release-diagnostics")
def release_diagnostics_command() -> None:
    """Show release diagnostics."""
    config = _bootstrap()
    diagnostics = release_diagnostics(config)
    _render_mapping_table(
        "Release Diagnostics",
        [
            ("release_latency_ms", f"{float(diagnostics.get('release_latency_ms', 0.0)):.2f}"),
            ("benchmark_diagnostics", ",".join(diagnostics.get("benchmark_diagnostics", [])) or "none"),
            ("stress_diagnostics", ",".join(diagnostics.get("stress_diagnostics", [])) or "none"),
            ("dependency_diagnostics", ",".join(diagnostics.get("dependency_diagnostics", [])) or "none"),
            ("security_diagnostics", ",".join(diagnostics.get("security_diagnostics", [])) or "none"),
        ],
    )


@app.command("release-benchmark")
def release_benchmark_command() -> None:
    """Show release benchmark payload."""
    config = _bootstrap()
    benchmark = release_benchmark(config)
    _render_mapping_table(
        "Release Benchmark",
        [
            ("detection_throughput", f"{float(benchmark.get('detection_throughput', 0.0)):.4f}"),
            ("mitigation_throughput", f"{float(benchmark.get('mitigation_throughput', 0.0)):.4f}"),
            ("streaming_throughput", f"{float(benchmark.get('streaming_throughput', 0.0)):.4f}"),
            ("cluster_throughput", f"{float(benchmark.get('cluster_throughput', 0.0)):.4f}"),
            ("benchmark_score", f"{float(benchmark.get('benchmark_score', 0.0)):.4f}"),
        ],
    )
    if float(benchmark.get("benchmark_score", 0.0)) <= 0.0:
        raise typer.Exit(code=1)


@app.command("release-security-audit")
def release_security_audit_command() -> None:
    """Show release security audit payload."""
    config = _bootstrap()
    audit = release_security_audit(config)
    _render_mapping_table(
        "Release Security Audit",
        [
            ("security_score", f"{float(audit.get('security_score', 0.0)):.4f}"),
            ("exposed_secret_count", str(int(audit.get("exposed_secret_count", 0)))),
            ("insecure_config_count", str(int(audit.get("insecure_config_count", 0)))),
            ("unsafe_dependency_patterns", str(int(audit.get("unsafe_dependency_patterns", 0)))),
            ("weak_deployment_config_count", str(int(audit.get("weak_deployment_config_count", 0)))),
            ("findings", ",".join(audit.get("findings", [])) or "none"),
        ],
    )
    if float(audit.get("security_score", 0.0)) < 0.4:
        raise typer.Exit(code=1)


@app.command()
def start() -> None:
    """Run one-command startup orchestration."""
    result = run_startup_command(console)
    if result.failed_checks:
        raise typer.Exit(code=1)


@app.command()
def stop() -> None:
    """Alias for lab stop."""
    lab_stop()


@app.command()
def status() -> None:
    """Alias for lab status."""
    lab_status()


@app.command()
def version() -> None:
    """Show installed version."""
    console.print(f"[bold]{APP_NAME}[/bold] {APP_VERSION}")


@app.command("welcome")
def welcome() -> None:
    """Render premium terminal onboarding."""
    render_welcome_screen(console)


@app.command("setup")
def setup() -> None:
    """Run interactive setup wizard."""
    run_setup_wizard()


@app.command("demo")
def demo(
    attack: str = typer.Option("udp_flood", "--attack"),
    attacker: str = typer.Option("h1", "--attacker"),
    victim: str = typer.Option("h2", "--victim"),
    probe: str = typer.Option("h3", "--probe"),
    target_ip: str = typer.Option("10.0.0.2", "--target-ip"),
    target_port: int = typer.Option(8081, "--target-port"),
    warmup: int = typer.Option(3, "--warmup"),
    attack_seconds: int = typer.Option(12, "--attack-seconds"),
    cooldown: int = typer.Option(5, "--cooldown"),
) -> None:
    """Run end-to-end live demo flow."""

    config = _bootstrap()
    failed = _render_failed_health(collect_static_health())
    if failed:
        if "runtime_assets" in failed:
            console.print("[bold yellow]Hint:[/bold yellow] runtime assets missing. Run `nsddos bootstrap download` if repo payloads are not present.")
        raise typer.Exit(code=1)

    startup = run_startup_command(console)
    if startup.failed_checks:
        raise typer.Exit(code=1)

    ui_url = startup.ui_url or DEFAULT_STARTUP_PROFILE.ui_url
    dashboard_url = _dashboard_url(ui_url)
    _open_browser(dashboard_url)

    report = run_live_attack_suite(
        config,
        attack=attack,
        attacker=attacker,
        victim=victim,
        probe=probe,
        target_ip=target_ip,
        target_port=target_port,
        warmup=warmup,
        attack_seconds=attack_seconds,
        cooldown=cooldown,
    )
    detection = evaluate_detection(config)
    mitigation_plan = evaluate_mitigation(config, detection=detection)
    mitigation = enforce_mitigation(config, mitigation_plan)

    _render_mapping_table(
        "NSDDOS Demo",
        [
            ("attack", attack),
            ("dashboard", dashboard_url),
            ("report_path", str(report.get("report_path", ""))),
            ("scenarios", str(len(report.get("scenarios", [])))),
            ("attack_detected", str(detection.attack_detected)),
            ("attack_type", detection.attack_type),
            ("confidence", f"{detection.confidence_score:.4f}"),
            ("mitigation_required", str(mitigation.mitigation_required)),
            ("mitigation_action", mitigation.mitigation_action),
            ("mitigation_status", mitigation.mitigation_status),
            ("execution_result", mitigation.execution_result),
        ],
    )

    if not detection.attack_detected:
        console.print("[bold red]Demo failed:[/bold red] detection engine did not classify live attack.")
        raise typer.Exit(code=1)
    if not mitigation.mitigation_required:
        console.print("[bold red]Demo failed:[/bold red] mitigation policy did not trigger.")
        raise typer.Exit(code=1)
    if mitigation.mitigation_status not in {"enforced", "verified"}:
        console.print(f"[bold red]Demo failed:[/bold red] mitigation ended in `{mitigation.mitigation_status}`.")
        raise typer.Exit(code=1)


@bootstrap_app.command("download")
def bootstrap_download(
    version: str | None = typer.Option(None, "--version"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Download and verify runtime asset bundle."""
    try:
        download_runtime_assets(version=version, force=force, console=console)
    except Exception as exc:
        console.print(f"[bold red]Runtime asset download failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def main() -> None:
    """Run CLI app."""
    app()


if __name__ == "__main__":
    main()

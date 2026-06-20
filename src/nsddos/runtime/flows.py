"""Flow visibility and safe traffic validation."""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from typing import Any

from nsddos.config import load_runtime_state
from nsddos.providers.docker_helper import helper_link_index_map, helper_running
from nsddos.providers.mininet.provider import MininetProvider
from nsddos.providers.sflow.provider import SFlowProvider
from nsddos.runtime.models import FlowState, TelemetryFreshness, VerificationResult


def _flow_signature(flow: dict[str, Any]) -> str:
    """Build stable flow signature."""
    keys = [
        "flowID",
        "name",
        "agent",
        "dataSource",
        "ifname",
        "inputifindex",
        "outputifindex",
        "source",
        "destination",
    ]
    values = [str(flow.get(key, "")) for key in keys if flow.get(key) is not None]
    return "|".join(values)


def _extract_interfaces(flows: list[dict[str, Any]]) -> list[str]:
    """Extract visible interfaces from flows."""
    names: set[str] = set()
    helper_links = helper_link_index_map() if helper_running() else {}
    for flow in flows:
        for key in ("ifname", "inputifname", "outputifname", "agent", "dataSource"):
            value = flow.get(key)
            if value:
                text = str(value)
                names.add(helper_links.get(text, text))
    return sorted(names)


def _extract_switches(flows: list[dict[str, Any]]) -> list[str]:
    """Extract switch-like sources."""
    names: set[str] = set()
    for flow in flows:
        for key in ("agent", "dataSource"):
            value = flow.get(key)
            if value:
                names.add(str(value))
    return sorted(names)


def sample_flow_visibility(config: dict[str, Any], interval: float = 2.0) -> FlowState:
    """Sample flow visibility twice, compare for movement."""
    provider = SFlowProvider(api_url=f"http://127.0.0.1:{config.get('api_port', 8008)}")
    status = provider.status()
    first = provider.flows() if status.get("reachable") else []
    time.sleep(interval)
    second = provider.flows() if status.get("reachable") else []
    first_sig = {_flow_signature(flow) for flow in first}
    second_sig = {_flow_signature(flow) for flow in second}
    changed = first_sig != second_sig
    flows = second if second else first
    return FlowState(
        collector_reachable=bool(status.get("reachable")),
        telemetry_present=bool(status.get("flows_accessible")),
        flow_count=len(flows),
        switches_visible=_extract_switches(flows),
        interfaces_visible=_extract_interfaces(flows),
        metrics_changed=changed,
        detail=f"first={len(first)} second={len(second)}",
    )


def telemetry_freshness(config: dict[str, Any], interval: float = 2.0) -> TelemetryFreshness:
    """Infer freshness from two flow samples."""
    provider = SFlowProvider(api_url=f"http://127.0.0.1:{config.get('api_port', 8008)}")
    observed_at = datetime.now(timezone.utc).isoformat()
    first = provider.flows() if provider.is_reachable() else []
    time.sleep(interval)
    second = provider.flows() if provider.is_reachable() else []
    changed = {_flow_signature(flow) for flow in first} != {_flow_signature(flow) for flow in second}
    flows = second if second else first
    stale = not changed and provider.is_reachable() and not flows
    last_flow_timestamp = observed_at
    return TelemetryFreshness(
        last_flow_timestamp=last_flow_timestamp,
        sample_interval_seconds=interval,
        stale=stale,
        detail=f"changed={changed} first={len(first)} second={len(second)}",
    )


def validate_traffic(config: dict[str, Any]) -> VerificationResult:
    """Run safe lightweight traffic validation."""
    state = load_runtime_state()
    mininet = MininetProvider(
        controller_port=config.get("lab", {}).get("controller_port", 6653),
        topology=config.get("lab", {}).get("mininet_topology", "single,3"),
    )
    if state.topology_state == "running":
        return VerificationResult(
            "traffic_validation",
            "warn",
            "active topology running; in-place safe probe not wired yet",
            "traffic",
        )
    if not mininet.is_installed():
        return VerificationResult(
            "traffic_validation",
            "warn",
            "Mininet not installed",
            "traffic",
        )
    try:
        command = [
            *mininet._command_prefix(),
            mininet._binary(),
            f"--controller=remote,ip={mininet.controller_host},port={mininet.controller_port}",
            f"--topo={mininet.topology}",
            "--test",
            "pingall",
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
        )
    except RuntimeError as exc:
        return VerificationResult("traffic_validation", "warn", str(exc), "traffic")
    except subprocess.TimeoutExpired:
        return VerificationResult("traffic_validation", "fail", "pingall timed out", "traffic")

    output = f"{result.stdout}\n{result.stderr}".strip()
    status = "pass" if result.returncode == 0 and "0% dropped" in output else "warn"
    return VerificationResult("traffic_validation", status, output[-500:] or "no output", "traffic")

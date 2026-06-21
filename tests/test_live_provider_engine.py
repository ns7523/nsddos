from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from subprocess import CompletedProcess

from nsddos.runtime.providers.live.connection_pool import ConnectionPolicy, DeterministicConnectionPool
from nsddos.runtime.providers.live.contracts import DistributionPoint, LiveTelemetrySnapshot, ProviderHealthRecord, TopologySnapshot
from nsddos.runtime.providers.live.floodlight import collect_floodlight_telemetry
from nsddos.runtime.providers.live.health import evaluate_provider_health
from nsddos.runtime.providers.live.mininet import collect_mininet_telemetry
from nsddos.runtime.providers.live.ovs import collect_ovs_telemetry
from nsddos.runtime.providers.live.sflow import collect_sflow_telemetry
from nsddos.runtime.providers.live.telemetry import collect_live_telemetry, live_snapshot_to_collection_state, snapshot_to_detection_telemetry
from nsddos.runtime.providers.live.validation import validate_live_snapshot


class _Pool:
    def __init__(self, mapping):
        self.mapping = mapping

    def get_json(self, url: str):
        return type("Result", (), self.mapping[url])()


def test_sflow_telemetry_ingestion():
    provider = type("Provider", (), {"api_url": "http://sflow", "is_reachable": lambda self: True})()
    pool = _Pool(
        {
            "http://sflow/flows/json?maxFlows=20&timeout=1": {
                "ok": True,
                "payload": [
                    {"source": "10.0.0.1", "destination_port": 80, "packets": 10, "bytes": 1000, "connections": 2, "syn_rate": 4, "ifname": "s1-eth1"},
                    {"source": "10.0.0.2", "destination_port": 53, "packets": 20, "bytes": 2000, "connections": 3, "udp_rate": 8, "ifname": "s1-eth2"},
                ],
                "latency_ms": 12.0,
            },
            "http://sflow/metric/ALL/json": {"ok": True, "payload": [{"drops": 2}], "latency_ms": 10.0},
            "http://sflow/topology/json": {"ok": True, "payload": {}, "latency_ms": 9.0},
        }
    )
    payload = collect_sflow_telemetry(provider, pool)

    assert payload["packet_rate"] == 30.0
    assert payload["byte_rate"] == 3000.0
    assert payload["active_flows"] == 2
    assert payload["source_ip_distribution"][0].key == "10.0.0.1"


def test_ovs_telemetry_ingestion():
    bridge = type("Bridge", (), {"name": "s1", "interfaces": ["s1-eth1"], "controller_connected": True})()
    state = type("State", (), {"installed": True, "service_running": True, "bridges": [bridge]})()
    provider = type("Provider", (), {"ovs_state": lambda self: state})()

    payload = collect_ovs_telemetry(provider)

    assert payload["reachable"] is True
    assert payload["bridges"] == ("s1",)
    assert payload["interfaces"] == ("s1-eth1",)


def test_mininet_topology_collection():
    status = {"installed": True, "running": True}
    metadata = type("Meta", (), {"switches": ["s1"], "hosts": ["h1", "h2"], "links": ["s1-h1", "s1-h2"], "controller": "127.0.0.1:6653", "controller_reachable": True})()
    provider = type(
        "Provider",
        (),
        {"status": lambda self: status, "topology_metadata": lambda self: metadata},
    )()

    payload = collect_mininet_telemetry(provider)

    assert payload["running"] is True
    assert payload["hosts"] == ("h1", "h2")


def test_floodlight_controller_collection():
    provider = type(
        "Provider",
        (),
        {
            "api_url": "http://flood",
            "is_reachable": lambda self: True,
            "controller_port_open": lambda self: True,
        },
    )()
    pool = _Pool(
        {
            "http://flood/wm/core/controller/switches/json": {"ok": True, "payload": [{"switchDPID": "00:01"}], "latency_ms": 8.0},
            "http://flood/wm/device/": {"ok": True, "payload": [{"ipv4": ["10.0.0.1"]}], "latency_ms": 7.0},
            "http://flood/wm/topology/links/json": {"ok": True, "payload": [{"src-switch": "00:01", "dst-switch": "00:02"}], "latency_ms": 6.0},
        }
    )

    payload = collect_floodlight_telemetry(provider, pool)

    assert payload["reachable"] is True
    assert payload["switches"] == ("00:01",)
    assert payload["hosts"] == ("10.0.0.1",)


def test_floodlight_provider_pushes_and_lists_static_flows():
    from nsddos.providers.floodlight.provider import FloodlightProvider

    state = {"entries": {}}

    class _Response:
        def __init__(self, payload):
            self.payload = payload
            self.status = 200

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _urlopen(request, timeout=3):
        method = request.get_method() if hasattr(request, "get_method") else "GET"
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if method == "POST" and url.endswith("/wm/staticflowentrypusher/json"):
            payload = json.loads(request.data.decode("utf-8"))
            state["entries"][payload["name"]] = payload
            return _Response({"status": "ok"})
        if method == "GET" and url.endswith("/wm/staticflowentrypusher/list/all/json"):
            return _Response({"00:00:00:00:00:00:00:01": state["entries"]})
        if method == "GET" and url.endswith("/wm/core/health/json"):
            return _Response({"healthy": True})
        return _Response({})

    provider = FloodlightProvider(api_url="http://flood")
    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr("nsddos.providers.floodlight.provider.urlopen", _urlopen)
    try:
        payload = {
            "switch": "00:00:00:00:00:00:00:01",
            "name": "rule-1",
            "active": "true",
            "priority": "50000",
            "eth_type": "0x0800",
            "src-ip": "10.0.0.8",
            "actions": "drop",
        }

        response = provider.push_static_flow(payload)

        assert response["status"] == "ok"
        assert provider.static_flow_exists("rule-1") is True
    finally:
        monkeypatch.undo()


def test_ovs_provider_installs_and_matches_drop_flow(monkeypatch):
    from nsddos.providers.ovs.provider import OVSProvider

    state = {"installed": False}

    def _run(args, require_root=False, timeout=5):
        if args[:2] == ["--timeout=1", "list-br"]:
            return CompletedProcess(args, 0, stdout="s1\n", stderr="")
        if args[:2] == ["list-ports", "s1"]:
            return CompletedProcess(args, 0, stdout="s1-eth1\ns1-eth2\n", stderr="")
        if args[:3] == ["get", "bridge", "s1"]:
            return CompletedProcess(args, 0, stdout="[]\n", stderr="")
        if args[:1] == ["show"]:
            return CompletedProcess(args, 0, stdout="is_connected: true\n", stderr="")
        if args[:2] == ["add-flow", "s1"]:
            state["installed"] = True
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[:3] == ["-O", "OpenFlow13", "dump-flows"] and args[3] == "s1":
            stdout = " cookie=0x0, duration=1.0s, table=0, n_packets=0, n_bytes=0, priority=50000,ip,nw_src=10.0.0.8 actions=drop\n" if state["installed"] else ""
            return CompletedProcess(args, 0, stdout=stdout, stderr="")
        raise AssertionError(f"unexpected ovs-ofctl args: {args}")

    monkeypatch.setattr("nsddos.providers.ovs.provider.helper_running", lambda: False)
    monkeypatch.setattr("nsddos.providers.ovs.provider.run_ovs_vsctl", _run)
    monkeypatch.setattr("nsddos.providers.ovs.provider.run_ovs_ofctl", _run)
    monkeypatch.setattr("nsddos.providers.ovs.provider.resolve_ovs_vsctl", lambda: "/usr/bin/ovs-vsctl")

    provider = OVSProvider()

    assert provider.install_drop_flow("s1", "priority=50000,ip,nw_src=10.0.0.8,actions=drop") is True
    assert provider.has_flow("s1", {"nw_src": "10.0.0.8", "actions": "drop"}) is True


def test_provider_health_degradation():
    health = evaluate_provider_health("sflowrt", reachable=True, latency_ms=5.0, malformed=True, last_timestamp=datetime.now(timezone.utc).isoformat())
    assert health.state == "degraded"


def test_timeout_handling():
    pool = DeterministicConnectionPool(ConnectionPolicy(timeout_seconds=0.01, retry_count=0))
    result = pool.get_json("http://127.0.0.1:1/never")
    assert result.ok is False


def test_malformed_telemetry_rejection():
    snapshot = LiveTelemetrySnapshot(
        provider_source="x",
        packet_rate=-1.0,
        byte_rate=10.0,
        connection_rate=1.0,
        syn_rate=0.0,
        udp_rate=0.0,
        icmp_rate=0.0,
        active_flows=1,
        dropped_packets=0,
        topology_state=TopologySnapshot(switches=("s1",), hosts=("h1",), controllers=("c1",)),
        timestamp=datetime.now(timezone.utc),
        health_state="healthy",
        provider_health=(ProviderHealthRecord("x", "healthy", True, 1.0, "ok"),),
    )
    assert "invalid_packet_counters" in validate_live_snapshot(snapshot)


def test_provider_reconnection_logic():
    health = evaluate_provider_health("sflowrt", reachable=False, latency_ms=0.0, malformed=False, error_count=2)
    assert health.state == "reconnecting"


def test_deterministic_telemetry_normalization(monkeypatch):
    from nsddos.runtime.providers.live import telemetry as telemetry_module

    snapshot_time = datetime(2100, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        telemetry_module,
        "build_live_provider_registry",
        lambda config: type("Registry", (), {"pool": None, "sflowrt": object(), "ovs": object(), "mininet": object(), "floodlight": object()})(),
    )
    monkeypatch.setattr(
        telemetry_module,
        "collect_sflow_telemetry",
        lambda provider, pool: {
            "reachable": True,
            "latency_ms": 1.0,
            "packet_rate": 10.0,
            "byte_rate": 100.0,
            "connection_rate": 2.0,
            "syn_rate": 1.0,
            "udp_rate": 0.0,
            "icmp_rate": 0.0,
            "active_flows": 1,
            "dropped_packets": 0,
            "source_ip_distribution": (DistributionPoint("10.0.0.1", 1.0),),
            "destination_port_distribution": (DistributionPoint("80", 1.0),),
            "interfaces": ("s1-eth1",),
            "raw_topology": {},
            "malformed": False,
        },
    )
    monkeypatch.setattr(telemetry_module, "collect_ovs_telemetry", lambda provider: {"reachable": True, "latency_ms": 0.0, "bridges": ("s1",), "interfaces": ("s1-eth1",), "active_connection_state": True, "dropped_packets": 0, "malformed": False})
    monkeypatch.setattr(telemetry_module, "collect_mininet_telemetry", lambda provider: {"reachable": True, "latency_ms": 0.0, "running": True, "switches": ("s1",), "hosts": ("h1",), "links": ("s1-h1",), "controller": "127.0.0.1:6653", "controller_reachable": True, "malformed": False})
    monkeypatch.setattr(telemetry_module, "collect_floodlight_telemetry", lambda provider, pool: {"reachable": True, "latency_ms": 0.0, "controller_port_open": True, "switches": ("s1",), "hosts": ("10.0.0.1",), "links": (), "malformed": False})
    monkeypatch.setattr(telemetry_module, "datetime", type("FakeDateTime", (), {"now": staticmethod(lambda tz=None: snapshot_time), "timezone": timezone}))

    first = collect_live_telemetry({"runtime": {"live": {"buffer_batch_size": 2}}})
    second = collect_live_telemetry({"runtime": {"live": {"buffer_batch_size": 2}}})

    assert first.to_dict() == second.to_dict()


def test_collection_path_unchanged_when_live_disabled(monkeypatch):
    from nsddos.runtime.collection import collectors as collectors_module

    monkeypatch.setattr(collectors_module, "runtime_registry", lambda config: {"x": object()})
    monkeypatch.setattr(collectors_module, "collect_provider_status_from_registry", lambda registry: {"sflowrt": {"reachable": True, "flows_accessible": True, "metrics_accessible": True, "topology_accessible": True}})
    monkeypatch.setattr(collectors_module, "sample_flow_visibility", lambda config, interval=1.0: collectors_module.FlowState(flow_count=1, telemetry_present=True))
    monkeypatch.setattr(collectors_module, "telemetry_freshness", lambda config, interval=1.0: collectors_module.TelemetryFreshness(last_flow_timestamp="2100-01-01T00:00:00+00:00", sample_interval_seconds=1.0))
    monkeypatch.setattr(collectors_module, "normalize_controller_topology", lambda config: type("C", (), {"to_dict": lambda self: {}})())
    monkeypatch.setattr(collectors_module, "detect_runtime_profile", lambda: type("P", (), {"to_dict": lambda self: {"name": "linux-native"}})())
    monkeypatch.setattr(collectors_module, "detect_runtime_capabilities", lambda: type("C", (), {"to_dict": lambda self: {"docker_daemon": True}})())
    monkeypatch.setattr(collectors_module, "validate_runtime_environment", lambda config: type("E", (), {"to_dict": lambda self: {"status": "compatible"}})())
    monkeypatch.setattr(collectors_module, "analyze_reproducibility", lambda config: type("R", (), {"to_dict": lambda self: {"status": "reproducible"}})())

    bundle = collectors_module.collect_runtime_state({"runtime": {"live": {"enabled": False}}})
    assert bundle.flow_state["flow_count"] == 1


def test_live_snapshot_feeds_collection_when_enabled(monkeypatch):
    from nsddos.runtime.collection import collectors as collectors_module

    snapshot = LiveTelemetrySnapshot(
        provider_source="live",
        packet_rate=10.0,
        byte_rate=100.0,
        connection_rate=2.0,
        syn_rate=1.0,
        udp_rate=0.0,
        icmp_rate=0.0,
        active_flows=1,
        dropped_packets=0,
        source_ip_distribution=(DistributionPoint("10.0.0.1", 1.0),),
        destination_port_distribution=(DistributionPoint("80", 1.0),),
        topology_state=TopologySnapshot(switches=("s1",), hosts=("h1",), controllers=("c1",)),
        timestamp=datetime(2100, 1, 1, tzinfo=timezone.utc),
        health_state="healthy",
        provider_health=(ProviderHealthRecord("sflowrt", "healthy", True, 1.0, "ok"),),
    )
    monkeypatch.setattr(collectors_module, "collect_live_telemetry", lambda config: snapshot)
    monkeypatch.setattr(collectors_module, "live_snapshot_to_collection_state", lambda item: live_snapshot_to_collection_state(snapshot))
    monkeypatch.setattr(collectors_module, "normalize_controller_topology", lambda config: type("C", (), {"to_dict": lambda self: {}})())
    monkeypatch.setattr(collectors_module, "detect_runtime_profile", lambda: type("P", (), {"to_dict": lambda self: {"name": "linux-native"}})())
    monkeypatch.setattr(collectors_module, "detect_runtime_capabilities", lambda: type("C", (), {"to_dict": lambda self: {"docker_daemon": True}})())
    monkeypatch.setattr(collectors_module, "validate_runtime_environment", lambda config: type("E", (), {"to_dict": lambda self: {"status": "compatible"}})())
    monkeypatch.setattr(collectors_module, "analyze_reproducibility", lambda config: type("R", (), {"to_dict": lambda self: {"status": "reproducible"}})())

    bundle = collectors_module.collect_runtime_state({"runtime": {"live": {"enabled": True}}})
    assert bundle.flow_state["flow_count"] == 1
    assert bundle.telemetry_state["collector_reachable"] is True


def test_snapshot_to_detection_payload():
    snapshot = LiveTelemetrySnapshot(
        provider_source="live",
        packet_rate=10.0,
        byte_rate=100.0,
        connection_rate=2.0,
        syn_rate=1.0,
        udp_rate=0.0,
        icmp_rate=0.0,
        active_flows=1,
        dropped_packets=0,
        source_ip_distribution=(DistributionPoint("10.0.0.1", 1.0),),
        destination_port_distribution=(DistributionPoint("80", 1.0),),
        topology_state=TopologySnapshot(switches=("s1",), hosts=("h1",), controllers=("c1",)),
        timestamp=datetime.now(timezone.utc) + timedelta(seconds=1),
        health_state="healthy",
        provider_health=(ProviderHealthRecord("sflowrt", "healthy", True, 1.0, "ok"),),
    )
    payload = snapshot_to_detection_telemetry(snapshot)
    assert payload["flows"][0]["source"] == "10.0.0.1"
    assert payload["flows"][0]["destination_port"] == 80

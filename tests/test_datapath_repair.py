from __future__ import annotations

from subprocess import CompletedProcess


def test_ovs_provider_marks_table_miss_only_as_not_forwarding(monkeypatch):
    from nsddos.providers.ovs.provider import OVSProvider

    def _run_vsctl(args, require_root=False, timeout=5):
        if args[:2] == ["--timeout=1", "list-br"]:
            return CompletedProcess(args, 0, stdout="s1\n", stderr="")
        if args[:2] == ["list-ports", "s1"]:
            return CompletedProcess(args, 0, stdout="s1-eth1\ns1-eth2\ns1-eth3\n", stderr="")
        if args[:3] == ["get", "bridge", "s1"]:
            if args[3] == "protocols":
                return CompletedProcess(args, 0, stdout='["OpenFlow13"]\n', stderr="")
            return CompletedProcess(args, 0, stdout="[]\n", stderr="")
        if args[:1] == ["show"]:
            return CompletedProcess(args, 0, stdout="is_connected: true\n", stderr="")
        raise AssertionError(f"unexpected ovs-vsctl args: {args}")

    def _run_ofctl(args, require_root=False, timeout=5):
        if args[:3] == ["-O", "OpenFlow13", "dump-flows"] and args[3] == "s1":
            return CompletedProcess(
                args,
                0,
                stdout=(
                    "NXST_FLOW reply (xid=0x4):\n"
                    " cookie=0x0, duration=10.0s, table=0, n_packets=1, n_bytes=42, "
                    "idle_age=0, priority=0 actions=CONTROLLER:65535\n"
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected ovs-ofctl args: {args}")

    monkeypatch.setattr("nsddos.providers.ovs.provider.RuntimeExecutor.lab_container_running", lambda self: True)
    monkeypatch.setattr("nsddos.providers.ovs.utils.RuntimeExecutor.lab_container_running", lambda self: True)
    monkeypatch.setattr("nsddos.providers.ovs.utils.ovs_process_running", lambda process_name='ovs-vswitchd': True)
    monkeypatch.setattr("nsddos.providers.ovs.provider.run_ovs_vsctl", _run_vsctl)
    monkeypatch.setattr("nsddos.providers.ovs.provider.run_ovs_ofctl", _run_ofctl)

    provider = OVSProvider(expected_protocol="OpenFlow13")

    assert provider.bridge_has_protocol("s1") is True
    assert provider.forwarding_programmed("s1") is False
    assert provider.status()["forwarding_programmed"] is False


def test_ovs_provider_installs_normal_flow_with_expected_protocol(monkeypatch):
    from nsddos.providers.ovs.provider import OVSProvider

    commands: list[list[str]] = []

    def _run_vsctl(args, require_root=False, timeout=5):
        if args[:2] == ["--timeout=1", "list-br"]:
            return CompletedProcess(args, 0, stdout="s1\n", stderr="")
        raise AssertionError(f"unexpected ovs-vsctl args: {args}")

    def _run_ofctl(args, require_root=False, timeout=5):
        commands.append(args)
        if args[:3] == ["-O", "OpenFlow13", "add-flow"]:
            return CompletedProcess(args, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected ovs-ofctl args: {args}")

    monkeypatch.setattr("nsddos.providers.ovs.provider.RuntimeExecutor.lab_container_running", lambda self: True)
    monkeypatch.setattr("nsddos.providers.ovs.utils.RuntimeExecutor.lab_container_running", lambda self: True)
    monkeypatch.setattr("nsddos.providers.ovs.provider.run_ovs_vsctl", _run_vsctl)
    monkeypatch.setattr("nsddos.providers.ovs.provider.run_ovs_ofctl", _run_ofctl)

    provider = OVSProvider(expected_protocol="OpenFlow13")

    assert provider.install_normal_flow("s1") is True
    assert commands[0] == ["-O", "OpenFlow13", "add-flow", "s1", "table=0,priority=0,actions=NORMAL"]


def test_mininet_helper_start_pins_openflow13(monkeypatch):
    from nsddos.providers.mininet.provider import MininetProvider

    commands: list[list[str]] = []

    class _State:
        topology_state = "stopped"
        topology_pid = None
        updated_at = None
        last_error = None
        provider_status = {}

    def _helper_exec(args, detached=False, timeout=30):
        commands.append(args)
        if args[:2] == ["sh", "-lc"] and "pkill -f '[l]abhost-mininet.py'" in args[2]:
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[:2] == ["sh", "-lc"] and args[2] == "mn -c":
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[:2] == ["sh", "-lc"] and "labhost-mininet.py" in args[2]:
            return CompletedProcess(args, 0, stdout="", stderr="")
        if args[:2] == ["pgrep", "-af"]:
            return CompletedProcess(args, 0, stdout="123 python3 /usr/local/bin/labhost-mininet.py\n", stderr="")
        if args[:2] == ["python3", "-c"]:
            return CompletedProcess(args, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected helper_exec args: {args}")

    monkeypatch.setattr("nsddos.providers.mininet.provider.RuntimeExecutor.lab_container_running", lambda self: True)
    monkeypatch.setattr(
        "nsddos.providers.mininet.provider.RuntimeExecutor.execute_lab",
        lambda self, args, detached=False, timeout=30: _helper_exec(args, detached=detached, timeout=timeout),
    )
    monkeypatch.setattr("nsddos.providers.mininet.provider.load_runtime_state", lambda: _State())
    monkeypatch.setattr("nsddos.providers.mininet.provider.write_runtime_state", lambda state: None)

    provider = MininetProvider(ovs_protocol="OpenFlow13")
    provider.start()

    start_command = next(
        args
        for args in commands
        if args[:2] == ["sh", "-lc"] and "nohup python3 /usr/local/bin/labhost-mininet.py" in args[2]
    )
    assert "OpenFlow13" in start_command[2]


def test_floodlight_provider_marks_openflow_version_error_as_inaccessible(monkeypatch):
    from nsddos.providers.floodlight.provider import FloodlightProvider

    class _Response:
        def __init__(self, payload):
            self.payload = payload
            self.status = 200

        def read(self):
            import json

            return json.dumps(self.payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _urlopen(url, timeout=3):
        target = url.full_url if hasattr(url, "full_url") else str(url)
        if target.endswith("/wm/core/health/json"):
            return _Response({"healthy": True})
        if target.endswith("/wm/core/controller/switches/json"):
            return _Response([{"switchDPID": "00:00:00:00:00:00:00:01"}])
        if target.endswith("/wm/core/switch/all/flow/json"):
            return _Response(
                {
                    "00:00:00:00:00:00:00:01": {
                        "*  ": "-- The request specified is not supported by the switch's OpenFlow version."
                    }
                }
            )
        raise AssertionError(f"unexpected url: {target}")

    monkeypatch.setattr("nsddos.providers.floodlight.provider.urlopen", _urlopen)

    provider = FloodlightProvider(api_url="http://flood")

    assert provider.flow_stats_accessible() is False
    assert provider.status()["flow_stats_accessible"] is False

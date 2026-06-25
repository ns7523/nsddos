from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from nsddos.cli import app


class _FakeTunnelProcess:
    def __init__(self, lines: list[str], returncode: int = 0) -> None:
        self.stdout = iter(lines)
        self._returncode = returncode
        self.terminated = False

    def wait(self) -> int:
        return self._returncode

    def terminate(self) -> None:
        self.terminated = True


def test_demo_runs_live_flow_with_summary(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr("nsddos.cli._bootstrap", lambda: {"logging": {"level": "INFO"}})
    monkeypatch.setattr(
        "nsddos.cli.collect_static_health",
        lambda: [SimpleNamespace(name="docker", ok=True, detail="ok")],
    )
    monkeypatch.setattr(
        "nsddos.cli.run_startup_command",
        lambda _console: SimpleNamespace(failed_checks=(), ui_url="http://127.0.0.1:8010"),
    )
    monkeypatch.setattr("nsddos.cli._open_browser", lambda url: url)
    monkeypatch.setattr(
        "nsddos.cli.run_live_attack_suite",
        lambda *args, **kwargs: {"report_path": "/tmp/demo-report.json", "scenarios": [{"attack_type": "udp_flood"}]},
    )
    detection = SimpleNamespace(
        attack_detected=True,
        attack_type="udp_flood",
        confidence_score=0.97,
    )
    mitigation_plan = SimpleNamespace(mitigation_required=True, mitigation_action="rate_limit")
    mitigation_result = SimpleNamespace(
        mitigation_required=True,
        mitigation_action="rate_limit",
        mitigation_status="verified",
        execution_result="traffic_blocked_verified",
    )
    monkeypatch.setattr("nsddos.cli.evaluate_detection", lambda _config: detection)
    monkeypatch.setattr("nsddos.cli.evaluate_mitigation", lambda _config, detection=None: mitigation_plan)
    monkeypatch.setattr("nsddos.cli.enforce_mitigation", lambda _config, _evaluation: mitigation_result)

    result = runner.invoke(app, ["demo"])

    assert result.exit_code == 0
    assert "NSDDOS Demo" in result.output
    assert "udp_flood" in result.output
    assert "verified" in result.output


def test_demo_fails_when_prereqs_missing(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr("nsddos.cli._bootstrap", lambda: {"logging": {"level": "INFO"}})
    monkeypatch.setattr(
        "nsddos.cli.collect_static_health",
        lambda: [SimpleNamespace(name="runtime_assets", ok=False, detail="missing")],
    )

    result = runner.invoke(app, ["demo"])

    assert result.exit_code == 1
    assert "runtime assets missing" in result.output.lower()


def test_ui_expose_requires_cloudflared(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr("nsddos.cli._bootstrap", lambda: {"logging": {"level": "INFO"}})
    monkeypatch.setattr("nsddos.cli.which", lambda _name: None)

    result = runner.invoke(app, ["ui", "expose"])

    assert result.exit_code == 1
    assert "cloudflared not found" in result.output.lower()


def test_ui_expose_prints_public_url(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr("nsddos.cli._bootstrap", lambda: {"logging": {"level": "INFO"}})
    monkeypatch.setattr("nsddos.cli.which", lambda _name: "/usr/local/bin/cloudflared")
    monkeypatch.setattr(
        "nsddos.cli.launch_ui_background",
        lambda: SimpleNamespace(reachable=True, ui_url="http://127.0.0.1:8010/"),
    )
    monkeypatch.setattr(
        "nsddos.cli.subprocess.Popen",
        lambda *args, **kwargs: _FakeTunnelProcess(
            [
                "INF Starting tunnel\n",
                "INF Route propagating to https://nsddos-demo.trycloudflare.com\n",
            ]
        ),
    )

    result = runner.invoke(app, ["ui", "expose"])

    assert result.exit_code == 0
    assert "Public UI:  https://nsddos-demo.trycloudflare.com" in result.output

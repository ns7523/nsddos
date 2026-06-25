"""Real Docker/runtime E2E validations."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
E2E_ENABLED = os.getenv("NSDDOS_E2E") == "1"

pytestmark = pytest.mark.e2e


def _entrypoint() -> list[str]:
    binary = shutil.which("nsddos")
    if binary:
        return [binary]
    return [sys.executable, "-m", "nsddos.cli"]


def _python_executable(env: dict[str, str]) -> str:
    binary = shutil.which("python", path=env.get("PATH"))
    return binary or sys.executable


def _ensure_import_path(env: dict[str, str]) -> None:
    probe = subprocess.run(
        [_python_executable(env), "-c", "import nsddos"],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if probe.returncode == 0 or "PYTHONPATH" in env:
        return
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")


def _run(
    args: list[str],
    *,
    env: dict[str, str],
    input_text: str | None = None,
    timeout: int = 900,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "command failed\n"
            f"CMD: {' '.join(args)}\n"
            f"CODE: {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    return result


def _docker_ready(env: dict[str, str]) -> bool:
    result = subprocess.run(
        ["docker", "info"],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    return result.returncode == 0


@pytest.fixture(scope="session")
def e2e_env(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    if not E2E_ENABLED:
        pytest.skip("Set NSDDOS_E2E=1 for real runtime E2E.")
    env = dict(os.environ)
    home_root = (
        Path(env["NSDDOS_HOME"])
        if env.get("NSDDOS_HOME")
        else tmp_path_factory.mktemp("nsddos-e2e-home") / "home"
    )
    home_root.mkdir(parents=True, exist_ok=True)
    env["NSDDOS_HOME"] = str(home_root)
    env.setdefault("NSDDOS_CONFIG", str(home_root / "config.yaml"))
    _ensure_import_path(env)
    if not _docker_ready(env):
        pytest.skip("Docker daemon unavailable for E2E.")
    bootstrap_url = env.get("NSDDOS_RUNTIME_ASSET_BASE_URL")
    if bootstrap_url:
        _run(_entrypoint() + ["bootstrap", "download"], env=env, timeout=600)
    setup_input = "1\n" + "y\n" * 12
    _run(_entrypoint() + ["setup"], env=env, input_text=setup_input, timeout=1800)
    _run(_entrypoint() + ["start"], env=env, timeout=1800)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with urlopen("http://127.0.0.1:8010/ui/healthz", timeout=3) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(1)
    else:
        raise AssertionError(
            "UI health endpoint did not become reachable after nsddos start"
        )
    return env


def test_runtime_commands_succeed(e2e_env: dict[str, str]) -> None:
    _run(_entrypoint() + ["health"], env=e2e_env)
    verbose = _run(_entrypoint() + ["health", "--verbose"], env=e2e_env)
    _run(_entrypoint() + ["doctor"], env=e2e_env)
    _run(_entrypoint() + ["lab", "start"], env=e2e_env)
    assert "mininet" in verbose.stdout.lower() or "ovs" in verbose.stdout.lower()


def test_start_creates_session_and_required_containers(e2e_env: dict[str, str]) -> None:
    session_path = Path(e2e_env["NSDDOS_HOME"]) / "session.json"
    assert session_path.exists()
    payload = json.loads(session_path.read_text(encoding="utf-8"))
    assert payload["ui_url"].startswith("http://127.0.0.1:")
    running = set(payload.get("running_containers", ()))
    assert {
        "nsddos-labhost",
        "nsddos-floodlight",
        "nsddos-sflowrt",
        "nsddos-detector",
    } <= running


def test_uvicorn_ui_app_boots_real(e2e_env: dict[str, str]) -> None:
    env = dict(e2e_env)
    process = subprocess.Popen(
        [
            _python_executable(env),
            "-m",
            "uvicorn",
            "nsddos.ui.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8011",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=5)
                raise AssertionError(
                    f"uvicorn exited early\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
                )
            try:
                with urlopen("http://127.0.0.1:8011/ui/healthz", timeout=2) as response:
                    body = response.read().decode("utf-8")
                assert response.status == 200
                assert body == '{"status":"ok"}'
                return
            except OSError:
                time.sleep(0.5)
        stdout, stderr = process.communicate(timeout=5)
        raise AssertionError(
            f"uvicorn did not become ready\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def test_real_attack_live_emits_report(e2e_env: dict[str, str]) -> None:
    result = _run(
        _entrypoint()
        + [
            "runtime",
            "attack-live",
            "--attack",
            "syn_flood",
            "--warmup",
            "1",
            "--attack-seconds",
            "3",
            "--cooldown",
            "1",
        ],
        env=e2e_env,
        timeout=1800,
    )
    assert "Live Attack Suite" in result.stdout
    assert "report_path" in result.stdout

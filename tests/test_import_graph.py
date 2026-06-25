"""Import graph and UI boot regressions."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_ROOT)
    return env


def _run_python(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def test_critical_imports_resolve_without_cycles() -> None:
    imports = (
        "import nsddos.ui.app",
        "import nsddos.api.app",
        "import nsddos.health",
        "import nsddos.bootstrap.runtime_boot",
        "import nsddos.runtime.verification.engine",
    )
    for statement in imports:
        result = _run_python(statement)
        assert result.returncode == 0, f"{statement}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def test_bootstrap_and_api_package_inits_are_lazy() -> None:
    checks = (
        PROJECT_ROOT / "src" / "nsddos" / "bootstrap" / "__init__.py",
        PROJECT_ROOT / "src" / "nsddos" / "api" / "__init__.py",
    )
    for path in checks:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("nsddos."):
                offenders.append(node.module)
        assert offenders == [], f"{path} eagerly imports {offenders}"


def test_uvicorn_ui_app_boots_and_answers_healthz() -> None:
    env = _env()
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "nsddos.ui.app:app", "--host", "127.0.0.1", "--port", "8011"],
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
                assert False, f"uvicorn exited early\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            try:
                with urlopen("http://127.0.0.1:8011/ui/healthz", timeout=2) as response:
                    body = response.read().decode("utf-8")
                assert response.status == 200
                assert body == '{"status":"ok"}'
                return
            except OSError:
                time.sleep(0.5)
        stdout, stderr = process.communicate(timeout=5)
        assert False, f"uvicorn did not become ready\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

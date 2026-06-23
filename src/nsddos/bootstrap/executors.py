"""Command executors for installer engine."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from nsddos.bootstrap.commands import SystemCommand
from nsddos.config import ensure_default_config, ensure_runtime_directories, ensure_runtime_state


@dataclass(frozen=True)
class CommandExecutionResult:
    """Result for installer command execution."""

    command: SystemCommand
    success: bool
    returncode: int
    stdout: str
    stderr: str


def run_system_command(command: SystemCommand) -> CommandExecutionResult:
    """Execute typed installer command."""

    if command.kind == "subprocess":
        try:
            completed = subprocess.run(
                command.argv,
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )
        except OSError as exc:
            return CommandExecutionResult(command, False, 1, "", str(exc))
        return CommandExecutionResult(
            command=command,
            success=completed.returncode == 0,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    if command.kind == "mkdir" and command.target_path:
        Path(command.target_path).mkdir(parents=True, exist_ok=True)
        return CommandExecutionResult(command, True, 0, command.target_path, "")
    if command.kind == "venv" and command.target_path:
        python_executable = command.python_executable or sys.executable
        completed = subprocess.run(
            (python_executable, "-m", "venv", command.target_path),
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
        return CommandExecutionResult(
            command=command,
            success=completed.returncode == 0,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    if command.kind == "runtime-init":
        ensure_runtime_directories()
        ensure_default_config()
        ensure_runtime_state()
        return CommandExecutionResult(command, True, 0, "runtime initialized", "")
    return CommandExecutionResult(command, False, 1, "", f"Unsupported command kind: {command.kind}")

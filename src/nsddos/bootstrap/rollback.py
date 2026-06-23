"""Rollback helpers for installer engine."""

from __future__ import annotations

import shutil
from pathlib import Path

from nsddos.bootstrap.commands import SystemCommand
from nsddos.bootstrap.executors import CommandExecutionResult, run_system_command


def rollback_command(command: SystemCommand) -> CommandExecutionResult | None:
    """Attempt rollback for single command when possible."""

    if command.kind == "venv" and command.target_path:
        path = Path(command.target_path)
        if path.exists():
            shutil.rmtree(path)
        return CommandExecutionResult(command=command, success=True, returncode=0, stdout="", stderr="")
    if command.kind == "subprocess" and command.rollback_argv:
        rollback = SystemCommand(
            kind="subprocess",
            description=f"Rollback {command.description}",
            argv=command.rollback_argv,
        )
        return run_system_command(rollback)
    return None


def rollback_commands(commands: tuple[SystemCommand, ...]) -> tuple[CommandExecutionResult, ...]:
    """Rollback reversible commands in reverse order."""

    results: list[CommandExecutionResult] = []
    for command in reversed(commands):
        if not (command.reversible or command.rollback_argv):
            continue
        result = rollback_command(command)
        if result is not None:
            results.append(result)
    return tuple(results)

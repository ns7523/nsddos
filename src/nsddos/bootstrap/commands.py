"""Typed command contracts for installer engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SystemCommand:
    """Typed executable command."""

    kind: str
    description: str
    argv: tuple[str, ...] = ()
    target_path: str | None = None
    python_executable: str | None = None
    rollback_argv: tuple[str, ...] = ()
    reversible: bool = False
    compose_args: tuple[str, ...] = ()
    runtime_version: str | None = None
    force: bool = False


def subprocess_command(
    description: str,
    argv: tuple[str, ...],
    rollback_argv: tuple[str, ...] = (),
    reversible: bool = False,
) -> SystemCommand:
    """Build subprocess-backed command."""

    return SystemCommand(
        kind="subprocess",
        description=description,
        argv=argv,
        rollback_argv=rollback_argv,
        reversible=reversible,
    )


def mkdir_command(description: str, target_path: str) -> SystemCommand:
    """Build directory creation command."""

    return SystemCommand(kind="mkdir", description=description, target_path=target_path)


def venv_command(
    description: str, python_executable: str, target_path: str
) -> SystemCommand:
    """Build virtualenv creation command."""

    return SystemCommand(
        kind="venv",
        description=description,
        target_path=target_path,
        python_executable=python_executable,
        reversible=True,
    )


def runtime_init_command(description: str) -> SystemCommand:
    """Build runtime initialization command."""

    return SystemCommand(kind="runtime-init", description=description)


def compose_subprocess_command(
    description: str, args: tuple[str, ...]
) -> SystemCommand:
    """Build compose-backed command resolved at execution time."""

    return SystemCommand(kind="compose", description=description, compose_args=args)


def asset_download_command(
    description: str, version: str | None = None, force: bool = False
) -> SystemCommand:
    """Build runtime asset download command."""

    return SystemCommand(
        kind="asset-download",
        description=description,
        runtime_version=version,
        force=force,
    )

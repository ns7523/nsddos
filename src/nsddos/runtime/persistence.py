"""Runtime persistence hardening."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from io import TextIOWrapper

from nsddos.runtime.domain.versions import SCHEMA_VERSION


class PersistenceError(RuntimeError):
    """Persistence integrity failure."""


def with_schema(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach schema version if missing."""
    data = dict(payload)
    data.setdefault("schema_version", SCHEMA_VERSION)
    return data


def _file_lock_path(path: Path) -> Path:
    return path.parent / f".{path.name}.lock"


def _directory_lock_path(path: Path) -> Path:
    return path / ".persistence.lock"


@contextmanager
def locked_file_path(path: Path) -> Iterator[TextIOWrapper]:
    """Acquire an exclusive sidecar lock for one logical file target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _file_lock_path(path)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def locked_persistence_scope(path_or_dir: Path) -> Iterator[TextIOWrapper]:
    """Acquire an exclusive bundle lock for a logical persistence directory."""
    bundle_dir = path_or_dir if path_or_dir.suffix == "" else path_or_dir.parent
    bundle_dir.mkdir(parents=True, exist_ok=True)
    lock_path = _directory_lock_path(bundle_dir)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_json(
    path: Path, payload: dict[str, Any], *, lock_scope: TextIOWrapper | None = None
) -> Path:
    """Atomically write JSON via temp file + replace."""
    if lock_scope is None:
        with locked_file_path(path) as handle:
            return atomic_write_json(path, payload, lock_scope=handle)

    path.parent.mkdir(parents=True, exist_ok=True)
    data = with_schema(payload)
    fd, temp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, separators=(",", ":"))
        os.replace(temp_path, path)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return path


def read_json_checked(path: Path) -> dict[str, Any]:
    """Read JSON with corruption + schema validation."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PersistenceError(f"corrupt json: {path}") from exc
    if not isinstance(payload, dict):
        raise PersistenceError(f"invalid json object: {path}")
    if payload.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise PersistenceError(f"unsupported schema: {payload.get('schema_version')}")
    return payload


def recover_json(
    path: Path, default: dict[str, Any], *, lock_scope: TextIOWrapper | None = None
) -> dict[str, Any]:
    """Recover corrupt/missing JSON with default payload."""
    if lock_scope is None:
        with locked_file_path(path) as handle:
            return recover_json(path, default, lock_scope=handle)

    try:
        return read_json_checked(path)
    except PersistenceError:
        atomic_write_json(path, default, lock_scope=lock_scope)
        return with_schema(default)
    except OSError:
        atomic_write_json(path, default, lock_scope=lock_scope)
        return with_schema(default)


def locked_update_json(
    path: Path,
    default: dict[str, Any],
    updater: Callable[[dict[str, Any]], dict[str, Any] | None],
    *,
    lock_scope: TextIOWrapper | None = None,
) -> dict[str, Any]:
    """Read, mutate, and atomically replace JSON under one lock scope."""
    if lock_scope is None:
        with locked_file_path(path) as handle:
            return locked_update_json(path, default, updater, lock_scope=handle)

    try:
        current = read_json_checked(path)
    except (PersistenceError, OSError):
        current = with_schema(default)
    updated = updater(dict(current))
    next_payload = with_schema(current if updated is None else updated)
    atomic_write_json(path, next_payload, lock_scope=lock_scope)
    return next_payload

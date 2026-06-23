"""Transaction logging for installer engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nsddos.bootstrap.commands import SystemCommand
from nsddos.constants import RUNTIME_DIR


@dataclass(frozen=True)
class TransactionRecord:
    """Single installer transaction record."""

    requirement_title: str
    command: SystemCommand
    status: str
    detail: str
    timestamp: str


@dataclass(frozen=True)
class TransactionLog:
    """Transaction log metadata."""

    path: Path


def transaction_log_path() -> Path:
    """Return transaction log path."""

    return RUNTIME_DIR / "setup-transactions.jsonl"


def create_transaction_log() -> TransactionLog:
    """Create transaction log handle."""

    path = transaction_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    return TransactionLog(path=path)


def append_transaction_record(log: TransactionLog, record: TransactionRecord) -> None:
    """Append transaction record."""

    payload = json.dumps(
        {
            "requirement_title": record.requirement_title,
            "command_kind": record.command.kind,
            "command_argv": list(record.command.argv),
            "target_path": record.command.target_path,
            "status": record.status,
            "detail": record.detail,
            "timestamp": record.timestamp,
        }
    )
    with log.path.open("a", encoding="utf-8") as handle:
        handle.write(payload + "\n")


def build_transaction_record(
    requirement_title: str,
    command: SystemCommand,
    status: str,
    detail: str,
) -> TransactionRecord:
    """Build transaction record with timestamp."""

    return TransactionRecord(
        requirement_title=requirement_title,
        command=command,
        status=status,
        detail=detail,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

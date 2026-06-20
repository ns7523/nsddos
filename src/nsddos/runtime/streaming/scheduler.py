"""Streaming scheduler helpers."""

from __future__ import annotations


def resolve_batch_size(config: dict) -> int:
    return int(config.get("runtime", {}).get("streaming", {}).get("batch_size", 64))

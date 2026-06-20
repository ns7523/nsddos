"""Runtime performance diagnostics."""

from __future__ import annotations

from time import monotonic
from typing import Callable, TypeVar

T = TypeVar("T")
PERFORMANCE_EVENTS: list[dict[str, float | str]] = []


def timed(name: str, timings: dict[str, float], fn: Callable[[], T]) -> T:
    """Run fn and record duration ms."""
    start = monotonic()
    try:
        return fn()
    finally:
        timings[name] = (monotonic() - start) * 1000


def empty_query_metrics() -> dict[str, float]:
    """Return query metric shape."""
    return {
        "query_execution_ms": 0.0,
        "selector_ms": 0.0,
        "graph_traversal_ms": 0.0,
        "replay_query_ms": 0.0,
        "pagination_ms": 0.0,
    }


def record_timing(name: str, duration_ms: float) -> None:
    """Record lightweight runtime timing event."""
    PERFORMANCE_EVENTS.append({"name": name, "duration_ms": duration_ms})

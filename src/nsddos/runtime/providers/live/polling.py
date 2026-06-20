"""Deterministic polling engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PollingResult(Generic[T]):
    value: T
    attempts: int
    timeout_triggered: bool


def poll_once(fetcher: Callable[[], T]) -> PollingResult[T]:
    return PollingResult(value=fetcher(), attempts=1, timeout_triggered=False)

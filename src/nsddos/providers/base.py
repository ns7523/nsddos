"""Provider base contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Base contract for runtime providers."""

    @abstractmethod
    def start(self) -> None:
        """Start provider runtime."""

    @abstractmethod
    def stop(self) -> None:
        """Stop provider runtime."""

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Return provider status."""


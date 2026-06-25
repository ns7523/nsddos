"""Read-only runtime API layer."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["create_app"]


def __getattr__(name: str) -> Any:
    if name != "create_app":
        raise AttributeError(name)
    value = getattr(import_module("nsddos.api.app"), name)
    globals()[name] = value
    return value

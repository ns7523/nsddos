"""API error helpers."""

from __future__ import annotations

from fastapi import HTTPException


class ApiError(RuntimeError):
    """Runtime API error."""


def raise_api_error(status_code: int, detail: str) -> None:
    """Raise typed HTTP error."""
    raise HTTPException(status_code=status_code, detail={"error": detail})

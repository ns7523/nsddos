"""Runtime query explainability."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.query.engine import explain_query_system


def explain_query_plan() -> dict[str, Any]:
    """Return query planning explanation."""
    system = explain_query_system()
    return {
        "query_count": len(system.get("queries", [])),
        "scope_count": len(system.get("scopes", [])),
        "dependency_count": len(system.get("dependencies", [])),
        **system,
    }

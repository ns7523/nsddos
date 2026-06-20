"""UI navigation."""

from __future__ import annotations


def render_navigation() -> str:
    links = [
        ("/ui", "Overview"),
        ("/ui/verification", "Verification"),
        ("/ui/convergence", "Convergence"),
        ("/ui/graph", "Graph"),
        ("/ui/timeline", "Timeline"),
        ("/ui/evidence", "Evidence"),
        ("/ui/replay", "Replay"),
        ("/ui/sessions", "Sessions"),
        ("/ui/service", "Service"),
        ("/ui/diagnostics", "Diagnostics"),
        ("/ui/drift", "Drift"),
        ("/ui/synchronization", "Synchronization"),
    ]
    anchors = "".join(f"<a href='{path}'>{label}</a>" for path, label in links)
    return f"<nav><strong>NSDDOS Observability</strong><br>{anchors}</nav><hr>"

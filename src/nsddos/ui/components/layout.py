"""UI layout helpers."""

from __future__ import annotations


def page_layout(title: str, nav: str, status_bar: str, body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title>"
        "<style>body{font-family:Arial,sans-serif;margin:16px;}table{border-collapse:collapse;width:100%;}"
        "th,td{border:1px solid #ccc;padding:6px;text-align:left;}nav a{margin-right:12px;}code{background:#f2f2f2;padding:2px 4px;}</style>"
        "</head><body>"
        f"{nav}{status_bar}<main>{body}</main>"
        "</body></html>"
    )

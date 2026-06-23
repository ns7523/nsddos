from __future__ import annotations

from pathlib import Path

from setuptools import setup


ROOT = Path(__file__).resolve().parent


def _collect_tree(relative_root: str) -> list[tuple[str, list[str]]]:
    base = ROOT / relative_root
    if not base.exists():
        return []

    grouped: dict[str, list[str]] = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        install_dir = path.parent.relative_to(ROOT).as_posix()
        grouped.setdefault(install_dir, []).append(path.relative_to(ROOT).as_posix())
    return sorted(grouped.items())


setup(
    data_files=[
        (
            ".",
            [
                "docker-compose.yml",
                ".env.example",
                "README.md",
                "LICENSE",
            ],
        ),
        *_collect_tree("docker"),
        *_collect_tree("deployment"),
        *_collect_tree("external"),
    ]
)

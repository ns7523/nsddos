"""Offline deterministic dependency audit."""

from __future__ import annotations

from pathlib import Path

from nsddos.constants import PROJECT_ROOT
from nsddos.release.contracts import DependencyAuditResult


def _parse_dependency_lines(
    pyproject_path: Path,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    lines = pyproject_path.read_text(encoding="utf-8").splitlines()
    deps: list[str] = []
    optional: list[str] = []
    section = ""
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("[project.optional-dependencies]"):
            section = "optional"
            continue
        if line.startswith("[project]"):
            section = "project"
            continue
        if line.startswith("[") and not line.startswith("[project"):
            section = ""
        if line.startswith('"') and line.endswith('",'):
            item = line.strip('",')
            if section == "project":
                deps.append(item)
            elif section == "optional":
                optional.append(item)
    return tuple(deps), tuple(optional)


def audit_dependencies(project_root: Path = PROJECT_ROOT) -> DependencyAuditResult:
    """Audit local dependency declarations without network access."""
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        return DependencyAuditResult("failed", 0, 0, 0, 1, 1, ("missing_pyproject",))

    dependencies, optional = _parse_dependency_lines(pyproject_path)
    package_count = len(dependencies)
    pinned_count = sum(1 for item in dependencies if "==" in item)
    bounded_count = sum(1 for item in dependencies if "<" in item and ">=" in item)
    conflict_count = len(dependencies) - len(
        set(item.split(">=")[0].split("==")[0].split("<")[0] for item in dependencies)
    )
    vulnerable_pattern_count = sum(
        1 for item in dependencies if item.endswith(">=0") or item.endswith("*")
    )
    findings: list[str] = []
    if not package_count:
        findings.append("missing_runtime_dependencies")
    if bounded_count < package_count:
        findings.append("unbounded_dependencies_present")
    if pinned_count == 0:
        findings.append("no_exact_pins_present")
    if conflict_count:
        findings.append("dependency_conflicts_detected")
    if vulnerable_pattern_count:
        findings.append("unsafe_dependency_patterns")
    if (
        package_count
        and conflict_count == 0
        and vulnerable_pattern_count == 0
        and bounded_count == package_count
    ):
        health = "healthy"
    elif (
        package_count
        and conflict_count == 0
        and vulnerable_pattern_count == 0
        and bounded_count > 0
    ):
        health = "healthy"
    elif package_count:
        health = "degraded"
    else:
        health = "failed"
    return DependencyAuditResult(
        dependency_health=health,
        package_count=package_count + len(optional),
        pinned_count=pinned_count,
        bounded_count=bounded_count,
        conflict_count=conflict_count,
        vulnerable_pattern_count=vulnerable_pattern_count,
        findings=tuple(findings),
    )

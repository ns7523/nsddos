"""Typed models for runtime asset resolution and downloads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeAssetFile:
    """One required downloaded file."""

    path: str
    sha256: str


@dataclass(frozen=True)
class RuntimeReleaseManifest:
    """Release manifest for one runtime bundle."""

    version: str
    bundle_name: str
    bundle_sha256: str
    required_files: tuple[RuntimeAssetFile, ...]
    required_directories: tuple[str, ...]
    release_tag: str
    schema_version: int = 1


@dataclass(frozen=True)
class RuntimeAssetStatus:
    """Resolved runtime asset state."""

    ready: bool
    source: str
    version: str
    root: Path
    compose_file: Path
    floodlight_jar: Path
    sflowrt_jar: Path
    detail: str


@dataclass(frozen=True)
class RuntimeAssetDownloadResult:
    """Download/materialization outcome."""

    downloaded: bool
    reused_cache: bool
    version: str
    root: Path
    compose_file: Path
    floodlight_jar: Path
    sflowrt_jar: Path
    detail: str

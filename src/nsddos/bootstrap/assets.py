"""Runtime asset resolution and download support."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from nsddos.bootstrap.assets_models import (
    RuntimeAssetDownloadResult,
    RuntimeAssetFile,
    RuntimeAssetStatus,
    RuntimeReleaseManifest,
)
from nsddos.constants import (
    APP_NAME,
    APP_VERSION,
    APP_ASSET_ROOT_ENV,
    APP_RUNTIME_ASSET_BASE_URL_ENV,
    APP_RUNTIME_VERSION_ENV,
    ASSET_CACHE_DIR,
    REPOSITORY_ROOT,
    RUNTIME_ASSET_BUNDLE_PATTERN,
    RUNTIME_ASSET_MANIFEST_PATTERN,
    RUNTIME_ASSET_RELEASE_REPO,
)

ACTIVE_RECEIPT_PATH = ASSET_CACHE_DIR / "active-runtime.json"
RELEASES_DIR = ASSET_CACHE_DIR / "releases"
PACKAGE_TEMPLATE_DIR = ASSET_CACHE_DIR / "templates" / "runtime"
RETRY_DELAYS = (0.0, 0.5, 1.0)
REQUIRED_REPO_FILES = (
    "external/floodlight/floodlight.jar",
    "external/floodlight/logback.xml",
    "external/floodlight/floodlightdefault.properties",
    "external/sflowrt/start.sh",
    "external/sflowrt/lib/sflowrt.jar",
)
REQUIRED_REPO_DIRECTORIES = (
    "external/sflowrt/app",
    "external/sflowrt/resources",
    "external/sflowrt/store",
    "docker",
)


def runtime_asset_version(version: str | None = None) -> str:
    """Return effective runtime asset version."""

    from os import getenv

    resolved = version or getenv(APP_RUNTIME_VERSION_ENV) or APP_VERSION or "unknown"
    return resolved.strip() or "unknown"


def _template_root() -> Path:
    resource = files("nsddos.bootstrap.templates").joinpath("runtime")
    with as_file(resource) as path:
        return path


def _receipt_payload(version: str, root: Path) -> dict[str, Any]:
    return {
        "app": APP_NAME,
        "version": version,
        "root": str(root),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_active_receipt(version: str, root: Path) -> None:
    ASSET_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_RECEIPT_PATH.write_text(
        json.dumps(_receipt_payload(version, root), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _read_active_receipt() -> dict[str, Any] | None:
    if not ACTIVE_RECEIPT_PATH.exists():
        return None
    try:
        payload = json.loads(ACTIVE_RECEIPT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _expected_paths(root: Path) -> tuple[Path, Path, Path]:
    return (
        root / "docker-compose.yml",
        root / "external" / "floodlight" / "floodlight.jar",
        root / "external" / "sflowrt" / "lib" / "sflowrt.jar",
    )


def _status_for_root(
    root: Path, source: str, version: str, detail: str
) -> RuntimeAssetStatus:
    compose_file, floodlight_jar, sflowrt_jar = _expected_paths(root)
    ready = compose_file.exists() and floodlight_jar.exists() and sflowrt_jar.exists()
    return RuntimeAssetStatus(
        ready=ready,
        source=source,
        version=version,
        root=root,
        compose_file=compose_file,
        floodlight_jar=floodlight_jar,
        sflowrt_jar=sflowrt_jar,
        detail=detail,
    )


def _repo_runtime_ready() -> bool:
    return all(
        (REPOSITORY_ROOT / relative).exists() for relative in REQUIRED_REPO_FILES
    ) and all(
        (REPOSITORY_ROOT / relative).exists() for relative in REQUIRED_REPO_DIRECTORIES
    )


def _cached_release_root(version: str) -> Path:
    return RELEASES_DIR / version


def release_manifest_name(version: str) -> str:
    """Return release manifest filename."""

    return RUNTIME_ASSET_MANIFEST_PATTERN.format(version=version)


def release_bundle_name(version: str) -> str:
    """Return release bundle filename."""

    return RUNTIME_ASSET_BUNDLE_PATTERN.format(version=version)


def release_download_base_url(version: str) -> str:
    """Return GitHub Releases download base URL."""

    from os import getenv

    override = getenv(APP_RUNTIME_ASSET_BASE_URL_ENV)
    if override:
        return override.rstrip("/")
    return (
        f"https://github.com/{RUNTIME_ASSET_RELEASE_REPO}/releases/download/v{version}"
    )


def release_manifest_url(version: str) -> str:
    """Return manifest download URL."""

    return f"{release_download_base_url(version)}/{release_manifest_name(version)}"


def release_bundle_url(version: str, bundle_name: str | None = None) -> str:
    """Return bundle download URL."""

    name = bundle_name or release_bundle_name(version)
    return f"{release_download_base_url(version)}/{name}"


def _download_bytes(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()


def _download_with_retry(url: str) -> bytes:
    last_error: Exception | None = None
    for delay in RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            return _download_bytes(url)
        except (OSError, URLError) as exc:
            last_error = exc
    raise RuntimeError(f"Download failed: {url}: {last_error}") from last_error


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_manifest(payload: bytes) -> RuntimeReleaseManifest:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid runtime manifest payload.") from exc
    if not isinstance(raw, dict):
        raise ValueError("Runtime manifest must be an object.")
    required = ("version", "bundle_name", "bundle_sha256", "required_files")
    missing = [field for field in required if field not in raw]
    if missing:
        raise ValueError(f"Runtime manifest missing fields: {', '.join(missing)}")
    raw_files = raw.get("required_files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("Runtime manifest required_files must be a non-empty list.")
    files_payload: list[RuntimeAssetFile] = []
    for item in raw_files:
        if not isinstance(item, dict):
            raise ValueError("Runtime manifest file entry invalid.")
        path = str(item.get("path", "")).strip()
        sha256 = str(item.get("sha256", "")).strip()
        if not path or not sha256:
            raise ValueError("Runtime manifest file entry missing path or sha256.")
        files_payload.append(RuntimeAssetFile(path=path, sha256=sha256))
    raw_dirs = raw.get("required_directories", ())
    required_directories = tuple(
        str(item).strip() for item in raw_dirs if str(item).strip()
    )
    version = str(raw.get("version", "")).strip()
    bundle_name = str(raw.get("bundle_name", "")).strip()
    bundle_sha256 = str(raw.get("bundle_sha256", "")).strip()
    if not version or not bundle_name or not bundle_sha256:
        raise ValueError("Runtime manifest values must be non-empty.")
    release_tag = str(raw.get("release_tag", f"v{version}")).strip() or f"v{version}"
    schema_version = int(raw.get("schema_version", 1))
    return RuntimeReleaseManifest(
        version=version,
        bundle_name=bundle_name,
        bundle_sha256=bundle_sha256,
        required_files=tuple(files_payload),
        required_directories=required_directories,
        release_tag=release_tag,
        schema_version=schema_version,
    )


def _copy_template_tree(target_root: Path) -> None:
    template_root = _template_root()
    for path in sorted(template_root.rglob("*")):
        relative = path.relative_to(template_root)
        destination = target_root / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def _verify_manifest(root: Path, manifest: RuntimeReleaseManifest) -> None:
    for relative in manifest.required_directories:
        path = root / relative
        if not path.exists():
            raise RuntimeError(
                f"Runtime asset directory missing after extraction: {relative}"
            )
    for item in manifest.required_files:
        path = root / item.path
        if not path.exists():
            raise RuntimeError(
                f"Runtime asset file missing after extraction: {item.path}"
            )
        digest = _sha256_file(path)
        if digest != item.sha256:
            raise RuntimeError(f"Runtime asset checksum mismatch: {item.path}")


def detect_runtime_asset_status(version: str | None = None) -> RuntimeAssetStatus:
    """Resolve current runtime asset location."""

    resolved_version = runtime_asset_version(version)
    from os import getenv

    override = getenv(APP_ASSET_ROOT_ENV)
    if override:
        return _status_for_root(
            Path(override).expanduser(),
            "override",
            resolved_version,
            f"{APP_ASSET_ROOT_ENV}={Path(override).expanduser()}",
        )
    if _repo_runtime_ready():
        return _status_for_root(
            REPOSITORY_ROOT,
            "repo",
            resolved_version,
            "repository runtime payloads available",
        )
    receipt = _read_active_receipt()
    if receipt:
        cached_version = str(receipt.get("version", resolved_version))
        cached_root = Path(
            str(receipt.get("root", _cached_release_root(cached_version)))
        ).expanduser()
        if cached_version == resolved_version or version is None:
            return _status_for_root(
                cached_root,
                "cache",
                cached_version,
                f"cached runtime assets: {cached_root}",
            )
    cached_root = _cached_release_root(resolved_version)
    if cached_root.exists():
        return _status_for_root(
            cached_root,
            "cache",
            resolved_version,
            f"cached runtime assets: {cached_root}",
        )
    return _status_for_root(
        PACKAGE_TEMPLATE_DIR,
        "package",
        resolved_version,
        "packaged templates available; runtime payload download required",
    )


def compose_file_path() -> Path:
    """Return effective compose file path."""

    return detect_runtime_asset_status().compose_file


def floodlight_jar_path() -> Path:
    """Return effective Floodlight jar path."""

    return detect_runtime_asset_status().floodlight_jar


def sflowrt_jar_path() -> Path:
    """Return effective sFlow-RT jar path."""

    return detect_runtime_asset_status().sflowrt_jar


def download_runtime_assets(
    *,
    version: str | None = None,
    force: bool = False,
    console: Console | None = None,
) -> RuntimeAssetDownloadResult:
    """Download, verify, and activate runtime assets."""

    resolved_version = runtime_asset_version(version)
    current = detect_runtime_asset_status(resolved_version)
    if (
        current.source == "cache"
        and current.ready
        and current.version == resolved_version
        and not force
    ):
        _write_active_receipt(current.version, current.root)
        return RuntimeAssetDownloadResult(
            downloaded=False,
            reused_cache=True,
            version=current.version,
            root=current.root,
            compose_file=current.compose_file,
            floodlight_jar=current.floodlight_jar,
            sflowrt_jar=current.sflowrt_jar,
            detail="Verified cache reused.",
        )

    manifest_url = release_manifest_url(resolved_version)
    active_console = console or Console()
    progress = Progress(
        SpinnerColumn(style="bright_cyan"),
        TextColumn("[bold white]{task.description}[/bold white]"),
        BarColumn(
            bar_width=24, complete_style="bright_cyan", finished_style="bright_cyan"
        ),
        TextColumn("[bright_cyan]{task.completed}/{task.total}[/bright_cyan]"),
        console=active_console,
        transient=console is not None,
    )
    task_id = progress.add_task("Runtime asset download", total=4, completed=0)
    if console is not None:
        active_console.print(progress)

    manifest_payload = _download_with_retry(manifest_url)
    manifest = _parse_manifest(manifest_payload)
    progress.update(task_id, advance=1)

    bundle_url = release_bundle_url(resolved_version, manifest.bundle_name)
    bundle_payload = _download_with_retry(bundle_url)
    if _sha256_bytes(bundle_payload) != manifest.bundle_sha256:
        raise RuntimeError("Runtime bundle checksum mismatch.")
    progress.update(task_id, advance=1)

    release_root = _cached_release_root(manifest.version)
    RELEASES_DIR.parent.mkdir(parents=True, exist_ok=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=RELEASES_DIR.parent) as temp_dir:
        temp_root = Path(temp_dir) / manifest.version
        temp_root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(bundle_payload), mode="r:gz") as archive:
            archive.extractall(temp_root)
        _copy_template_tree(temp_root)
        _verify_manifest(temp_root, manifest)
        progress.update(task_id, advance=1)
        if release_root.exists():
            shutil.rmtree(release_root)
        shutil.move(str(temp_root), str(release_root))

    _write_active_receipt(manifest.version, release_root)
    progress.update(task_id, advance=1)
    status = _status_for_root(
        release_root, "cache", manifest.version, f"downloaded from {bundle_url}"
    )
    if not status.ready:
        raise RuntimeError(
            "Runtime asset download completed but required paths are still missing."
        )
    if console is not None:
        active_console.print(
            Panel(
                "\n".join(
                    (
                        f"[bold white]Version[/bold white]  {status.version}",
                        f"[bold white]Root[/bold white]  {status.root}",
                        f"[bold white]Compose[/bold white]  {status.compose_file}",
                    )
                ),
                title="Runtime Assets Ready",
                border_style="green",
            )
        )
    return RuntimeAssetDownloadResult(
        downloaded=True,
        reused_cache=False,
        version=status.version,
        root=status.root,
        compose_file=status.compose_file,
        floodlight_jar=status.floodlight_jar,
        sflowrt_jar=status.sflowrt_jar,
        detail=f"Downloaded runtime assets from {bundle_url}",
    )

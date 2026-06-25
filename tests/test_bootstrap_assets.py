from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

from nsddos.bootstrap import assets
from nsddos.bootstrap.assets_models import RuntimeAssetStatus


def _template_tree(root: Path) -> None:
    (root / "docker").mkdir(parents=True, exist_ok=True)
    (root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (root / "docker" / "labhost.Dockerfile").write_text(
        "FROM ubuntu:22.04\n", encoding="utf-8"
    )
    (root / "external" / "sflowrt" / "app").mkdir(parents=True, exist_ok=True)
    (root / "external" / "sflowrt" / "resources").mkdir(parents=True, exist_ok=True)
    (root / "external" / "sflowrt" / "store").mkdir(parents=True, exist_ok=True)


def _bundle_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for relative, payload in files.items():
            info = tarfile.TarInfo(name=relative)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def _manifest_dict(
    version: str, bundle_name: str, bundle_payload: bytes, files: dict[str, bytes]
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "version": version,
        "release_tag": f"v{version}",
        "bundle_name": bundle_name,
        "bundle_sha256": hashlib.sha256(bundle_payload).hexdigest(),
        "required_directories": [
            "external/sflowrt/app",
            "external/sflowrt/resources",
            "external/sflowrt/store",
            "docker",
        ],
        "required_files": [
            {"path": relative, "sha256": hashlib.sha256(payload).hexdigest()}
            for relative, payload in files.items()
        ],
    }


def test_detect_runtime_asset_status_prefers_repo(monkeypatch, tmp_path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "external" / "floodlight").mkdir(parents=True, exist_ok=True)
    (repo_root / "external" / "sflowrt" / "lib").mkdir(parents=True, exist_ok=True)
    (repo_root / "external" / "sflowrt" / "app").mkdir(parents=True, exist_ok=True)
    (repo_root / "external" / "sflowrt" / "resources").mkdir(
        parents=True, exist_ok=True
    )
    (repo_root / "external" / "sflowrt" / "store").mkdir(parents=True, exist_ok=True)
    (repo_root / "docker").mkdir(parents=True, exist_ok=True)
    (repo_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (repo_root / "external" / "floodlight" / "floodlight.jar").write_bytes(b"jar")
    (repo_root / "external" / "floodlight" / "logback.xml").write_text(
        "xml", encoding="utf-8"
    )
    (repo_root / "external" / "floodlight" / "floodlightdefault.properties").write_text(
        "cfg", encoding="utf-8"
    )
    (repo_root / "external" / "sflowrt" / "start.sh").write_text(
        "run", encoding="utf-8"
    )
    (repo_root / "external" / "sflowrt" / "lib" / "sflowrt.jar").write_bytes(b"sflow")

    monkeypatch.setattr(assets, "REPOSITORY_ROOT", repo_root)

    status = assets.detect_runtime_asset_status("0.9.0b2")

    assert status.ready is True
    assert status.source == "repo"
    assert status.compose_file == repo_root / "docker-compose.yml"


def test_manifest_parser_rejects_missing_fields() -> None:
    try:
        assets._parse_manifest(b'{"version": "0.9.0b2"}')
    except ValueError as exc:
        assert "missing fields" in str(exc)
    else:
        assert False, "expected manifest parse failure"


def test_download_runtime_assets_downloads_and_reuses_cache(
    monkeypatch, tmp_path
) -> None:
    cache_root = tmp_path / "cache"
    release_version = "0.9.0b2"
    bundle_name = f"nsddos-runtime-{release_version}.tar.gz"
    files = {
        "external/floodlight/floodlight.jar": b"floodlight-jar",
        "external/floodlight/logback.xml": b"<xml />",
        "external/floodlight/floodlightdefault.properties": b"key=value",
        "external/sflowrt/start.sh": b"#!/bin/sh\n",
        "external/sflowrt/lib/sflowrt.jar": b"sflowrt-jar",
    }
    bundle_payload = _bundle_bytes(files)
    manifest_payload = json.dumps(
        _manifest_dict(release_version, bundle_name, bundle_payload, files)
    ).encode("utf-8")

    template_root = tmp_path / "templates"
    _template_tree(template_root)

    monkeypatch.setattr(assets, "ASSET_CACHE_DIR", cache_root)
    monkeypatch.setattr(
        assets, "ACTIVE_RECEIPT_PATH", cache_root / "active-runtime.json"
    )
    monkeypatch.setattr(assets, "RELEASES_DIR", cache_root / "releases")
    monkeypatch.setattr(
        assets, "PACKAGE_TEMPLATE_DIR", cache_root / "templates" / "runtime"
    )
    monkeypatch.setattr(assets, "_template_root", lambda: template_root)
    monkeypatch.setattr(assets, "REPOSITORY_ROOT", tmp_path / "missing-repo")

    calls: list[str] = []

    def fake_download(url: str) -> bytes:
        calls.append(url)
        if url.endswith(".manifest.json"):
            return manifest_payload
        if url.endswith(".tar.gz"):
            return bundle_payload
        raise AssertionError(url)

    monkeypatch.setattr(assets, "_download_with_retry", fake_download)

    result = assets.download_runtime_assets(version=release_version)
    reused = assets.download_runtime_assets(version=release_version)
    forced = assets.download_runtime_assets(version=release_version, force=True)

    assert result.downloaded is True
    assert result.root == cache_root / "releases" / release_version
    assert result.compose_file.exists()
    assert result.floodlight_jar.exists()
    assert result.sflowrt_jar.exists()
    assert reused.reused_cache is True
    assert forced.downloaded is True
    assert len(calls) == 4


def test_detect_runtime_asset_status_uses_override(monkeypatch, tmp_path) -> None:
    root = tmp_path / "override"
    _template_tree(root)
    (root / "external" / "floodlight").mkdir(parents=True, exist_ok=True)
    (root / "external" / "sflowrt" / "lib").mkdir(parents=True, exist_ok=True)
    (root / "external" / "floodlight" / "floodlight.jar").write_bytes(b"jar")
    (root / "external" / "sflowrt" / "lib" / "sflowrt.jar").write_bytes(b"jar")
    monkeypatch.setenv("NSDDOS_ASSET_ROOT", str(root))

    status = assets.detect_runtime_asset_status("0.9.0b2")

    assert isinstance(status, RuntimeAssetStatus)
    assert status.source == "override"
    assert status.ready is True


def test_release_download_base_url_uses_override(monkeypatch) -> None:
    monkeypatch.setenv(
        "NSDDOS_RUNTIME_ASSET_BASE_URL", "http://127.0.0.1:8999/runtime/"
    )

    base_url = assets.release_download_base_url("0.9.0b2")
    manifest_url = assets.release_manifest_url("0.9.0b2")
    bundle_url = assets.release_bundle_url("0.9.0b2")

    assert base_url == "http://127.0.0.1:8999/runtime"
    assert manifest_url.endswith("/nsddos-runtime-0.9.0b2.manifest.json")
    assert bundle_url.endswith("/nsddos-runtime-0.9.0b2.tar.gz")

from __future__ import annotations

import importlib.util
import json
import tarfile
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "build_runtime_release.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("build_runtime_release", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runtime_release_builder_outputs_bundle_and_manifest(tmp_path):
    module = _load_module()
    repo_root = tmp_path / "repo"
    output_dir = tmp_path / "dist"

    (repo_root / "external/floodlight").mkdir(parents=True)
    (repo_root / "external/sflowrt/lib").mkdir(parents=True)
    (repo_root / "docker").mkdir(parents=True)
    (repo_root / "external/floodlight/floodlight.jar").write_bytes(b"floodlight")
    (repo_root / "external/sflowrt/lib/sflowrt.jar").write_bytes(b"sflowrt")
    (repo_root / "docker/floodlight.Dockerfile").write_text(
        "FROM scratch\n", encoding="utf-8"
    )
    (repo_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    bundle_path, manifest_path = module.build_runtime_release(
        repo_root=repo_root,
        output_dir=output_dir,
        version="0.9.0b2",
        github_repo="ns7523/nsddos",
        tag="v0.9.0b2",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert bundle_path.name == "nsddos-runtime-0.9.0b2.tar.gz"
    assert manifest["version"] == "0.9.0b2"
    assert manifest["bundle"] == bundle_path.name
    assert manifest["bundle_name"] == bundle_path.name
    assert manifest["sha256"] == manifest["bundle_sha256"]
    assert manifest["release_url"].endswith(f"/v0.9.0b2/{bundle_path.name}")

    with tarfile.open(bundle_path, mode="r:gz") as archive:
        names = sorted(archive.getnames())
    assert "docker-compose.yml" in names
    assert "docker/floodlight.Dockerfile" in names
    assert "external/floodlight/floodlight.jar" in names
    assert "external/sflowrt/lib/sflowrt.jar" in names

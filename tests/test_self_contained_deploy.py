from __future__ import annotations

import tomllib

import yaml

from nsddos.constants import COMPOSE_FILE, FLOODLIGHT_JAR, REPOSITORY_ROOT, SFLOWRT_JAR


def test_default_compose_file_points_to_repo_root() -> None:
    assert COMPOSE_FILE == REPOSITORY_ROOT / "docker-compose.yml"


def test_internal_runtime_assets_exist() -> None:
    assert FLOODLIGHT_JAR == REPOSITORY_ROOT / "external" / "floodlight" / "floodlight.jar"
    assert SFLOWRT_JAR == REPOSITORY_ROOT / "external" / "sflowrt" / "lib" / "sflowrt.jar"
    assert FLOODLIGHT_JAR.exists()
    assert (REPOSITORY_ROOT / "external" / "floodlight" / "floodlightdefault.properties").exists()
    assert SFLOWRT_JAR.exists()
    assert (REPOSITORY_ROOT / "external" / "sflowrt" / "app").is_dir()
    assert (REPOSITORY_ROOT / "external" / "sflowrt" / "resources").is_dir()
    assert (REPOSITORY_ROOT / "external" / "sflowrt" / "store").is_dir()


def test_compose_files_stay_within_repo_boundary() -> None:
    compose_paths = (
        REPOSITORY_ROOT / "docker-compose.yml",
        REPOSITORY_ROOT / "docker" / "runtime" / "base" / "docker-compose.base.yml",
        REPOSITORY_ROOT / "docker" / "runtime" / "dev" / "docker-compose.dev.yml",
        REPOSITORY_ROOT / "docker" / "runtime" / "research" / "docker-compose.research.yml",
    )
    for path in compose_paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "services" in payload
        for service in payload["services"].values():
            build = service.get("build")
            if not isinstance(build, dict):
                continue
            dockerfile = str(build.get("dockerfile", ""))
            assert "/".join(("code", "nsddos")) not in dockerfile
            if path == REPOSITORY_ROOT / "docker-compose.yml":
                assert str(build.get("context")) == "."


def test_repo_has_no_stale_monorepo_paths() -> None:
    checked_paths = (
        REPOSITORY_ROOT / "docker-compose.yml",
        REPOSITORY_ROOT / "docker" / "labhost.Dockerfile",
        REPOSITORY_ROOT / "docker" / "floodlight.Dockerfile",
        REPOSITORY_ROOT / "docker" / "sflowrt.Dockerfile",
        REPOSITORY_ROOT / "README.md",
        REPOSITORY_ROOT / "src" / "nsddos" / "constants.py",
    )
    banned = (
        "/".join(("code", "nsddos")),
        "context: " + "../..",
        "dockerfile: " + "/".join(("code", "nsddos")),
        "/".join(("", "Users", "143ns")),
        "<" * 7,
        ">" * 7,
    )
    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for pattern in banned:
            assert pattern not in text, f"{pattern} leaked in {path}"


def test_manifest_excludes_repo_runtime_payloads() -> None:
    manifest = (REPOSITORY_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include docker *" not in manifest
    assert "recursive-include deployment *" not in manifest
    assert "recursive-include external *" not in manifest
    assert "include docker-compose.yml" not in manifest
    assert "include .env.example" in manifest


def test_setup_py_does_not_package_runtime_payloads_for_wheel() -> None:
    setup_py = (REPOSITORY_ROOT / "setup.py").read_text(encoding="utf-8")
    assert "data_files" not in setup_py
    assert "_collect_tree(" not in setup_py
    assert "docker-compose.yml" not in setup_py
    assert "\"external\"" not in setup_py


def test_pyproject_limits_packaged_assets_to_in_package_ui_files() -> None:
    pyproject = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    setuptools_cfg = pyproject["tool"]["setuptools"]
    package_data = setuptools_cfg["package-data"]["nsddos"]

    assert setuptools_cfg["include-package-data"] is True
    assert "ui/templates/**/*.html" in package_data
    assert "ui/static/**/*.css" in package_data
    assert "ui/static/**/*.js" in package_data
    assert "ui/static/**/*.ttf" in package_data

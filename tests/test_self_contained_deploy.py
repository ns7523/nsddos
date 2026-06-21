from __future__ import annotations

import yaml

from nsddos.constants import COMPOSE_FILE, FLOODLIGHT_JAR, REPOSITORY_ROOT, SFLOWRT_JAR


def test_default_compose_file_points_to_repo_root() -> None:
    assert COMPOSE_FILE == REPOSITORY_ROOT / "docker-compose.yml"


def test_internal_runtime_assets_exist() -> None:
    assert FLOODLIGHT_JAR == REPOSITORY_ROOT / "external" / "floodlight" / "floodlight.jar"
    assert SFLOWRT_JAR == REPOSITORY_ROOT / "external" / "sflowrt" / "lib" / "sflowrt.jar"
    assert FLOODLIGHT_JAR.exists()
    assert SFLOWRT_JAR.exists()
    assert (REPOSITORY_ROOT / "external" / "sflowrt" / "app").is_dir()
    assert (REPOSITORY_ROOT / "external" / "sflowrt" / "resources").is_dir()
    assert (REPOSITORY_ROOT / "external" / "sflowrt" / "store").is_dir()


def test_compose_files_stay_within_repo_boundary() -> None:
    compose_paths = (
        REPOSITORY_ROOT / "docker-compose.yml",
        REPOSITORY_ROOT / "code" / "nsddos" / "docker-compose.yml",
        REPOSITORY_ROOT / "code" / "nsddos" / "docker" / "docker-compose.yml",
    )
    for path in compose_paths:
        text = path.read_text(encoding="utf-8")
        assert "../../../" not in text
        payload = yaml.safe_load(text)
        assert "services" in payload

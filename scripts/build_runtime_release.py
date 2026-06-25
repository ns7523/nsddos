#!/usr/bin/env python3
"""Build runtime release bundle and manifest for GitHub Releases."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path


BUNDLE_DIRECTORIES = (
    "external/floodlight",
    "external/sflowrt",
    "docker",
)
BUNDLE_FILES = ("docker-compose.yml",)


def sha256_file(path: Path) -> str:
    """Return SHA256 digest for file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_bundle_paths(repo_root: Path) -> list[Path]:
    """Collect runtime asset paths for bundle."""

    members: list[Path] = []
    for relative in BUNDLE_DIRECTORIES:
        root = repo_root / relative
        if not root.is_dir():
            raise FileNotFoundError(f"Missing runtime directory: {relative}")
        for path in sorted(root.rglob("*")):
            if path.is_file():
                members.append(path)
    for relative in BUNDLE_FILES:
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Missing runtime file: {relative}")
        members.append(path)
    return members


def bundle_name(version: str) -> str:
    return f"nsddos-runtime-{version}.tar.gz"


def manifest_name(version: str) -> str:
    return f"nsddos-runtime-{version}.manifest.json"


def build_runtime_release(
    *,
    repo_root: Path,
    output_dir: Path,
    version: str,
    github_repo: str,
    tag: str,
) -> tuple[Path, Path]:
    """Build runtime bundle and manifest files."""

    members = collect_bundle_paths(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle_path = output_dir / bundle_name(version)
    manifest_path = output_dir / manifest_name(version)
    release_url = f"https://github.com/{github_repo}/releases/download/{tag}/{bundle_path.name}"

    with tarfile.open(bundle_path, mode="w:gz") as archive:
        for path in members:
            archive.add(path, arcname=path.relative_to(repo_root))

    manifest = {
        "version": version,
        "schema_version": 1,
        "release_tag": tag,
        "bundle": bundle_path.name,
        "bundle_name": bundle_path.name,
        "bundle_sha256": sha256_file(bundle_path),
        "sha256": sha256_file(bundle_path),
        "size": bundle_path.stat().st_size,
        "release_url": release_url,
        "required_directories": sorted(BUNDLE_DIRECTORIES),
        "required_files": [
            {
                "path": str(path.relative_to(repo_root)),
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
            for path in members
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle_path, manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release version without v prefix.")
    parser.add_argument("--github-repo", required=True, help="GitHub owner/repo slug.")
    parser.add_argument("--tag", help="Git tag. Defaults to v<version>.")
    parser.add_argument("--repo-root", default=".", help="Repository root containing runtime assets.")
    parser.add_argument("--output-dir", default="dist/runtime-release", help="Artifact output directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    tag = args.tag or f"v{args.version}"
    bundle_path, manifest_path = build_runtime_release(
        repo_root=repo_root,
        output_dir=output_dir,
        version=args.version,
        github_repo=args.github_repo,
        tag=tag,
    )
    print(bundle_path)
    print(manifest_path)


if __name__ == "__main__":
    main()

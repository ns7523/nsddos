"""Deterministic release artifact generation."""

from __future__ import annotations

import hashlib

from nsddos.release.contracts import ArtifactMetadata, PackageMetadata, ReleaseCandidateEvaluation


def build_artifacts(
    package_metadata: PackageMetadata,
    release_id: str,
    checksum_algorithm: str,
) -> tuple[ArtifactMetadata, ...]:
    """Build deterministic artifact metadata."""
    artifact_specs = (
        ("release-archive", package_metadata.archive_name),
        ("deployment-bundle", f"{package_metadata.bundle_name}.bundle"),
        ("release-manifest", f"{package_metadata.bundle_name}.manifest.json"),
    )
    artifacts: list[ArtifactMetadata] = []
    for artifact_type, name in artifact_specs:
        checksum = hashlib.new(checksum_algorithm, f"{release_id}:{artifact_type}:{name}".encode("utf-8")).hexdigest()
        signature = hashlib.new(checksum_algorithm, f"sig:{checksum}".encode("utf-8")).hexdigest()
        artifacts.append(
            ArtifactMetadata(
                artifact_id=f"{release_id}:{artifact_type}",
                path=name,
                checksum=checksum,
                signature=signature,
                artifact_type=artifact_type,
            )
        )
    return tuple(artifacts)


def artifacts_payload(evaluation: ReleaseCandidateEvaluation) -> dict:
    """Return persisted artifact payload shape."""
    return {"artifacts": [item.to_dict() for item in evaluation.artifacts]}

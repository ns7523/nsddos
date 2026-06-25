"""High-level runtime collection layer."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.collection.aggregation import aggregate_collection
from nsddos.runtime.collection.snapshots import write_collection_snapshot
from nsddos.runtime.models import RuntimeCollectionBundle


def collect_runtime_bundle(
    config: dict[str, Any], persist: bool = False
) -> RuntimeCollectionBundle:
    """Collect normalized runtime state."""
    bundle = aggregate_collection(config)
    if persist:
        write_collection_snapshot(bundle)
    return bundle

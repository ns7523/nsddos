"""Runtime collection aggregation."""

from __future__ import annotations

from nsddos.runtime.collection.collectors import collect_runtime_state
from nsddos.runtime.collection.normalization import normalize_collection
from nsddos.runtime.models import RuntimeCollectionBundle


def aggregate_collection(config: dict) -> RuntimeCollectionBundle:
    """Collect + normalize runtime collection state."""
    return normalize_collection(collect_runtime_state(config))

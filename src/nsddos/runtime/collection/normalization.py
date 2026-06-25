"""Runtime collection normalization."""

from __future__ import annotations

from nsddos.runtime.models import RuntimeCollectionBundle, SCHEMA_VERSION


def normalize_collection(bundle: RuntimeCollectionBundle) -> RuntimeCollectionBundle:
    """Normalize collection bundle shape."""
    bundle.schema_version = bundle.schema_version or SCHEMA_VERSION
    bundle.provider_status = dict(bundle.provider_status)
    bundle.timings = dict(bundle.timings)
    return bundle

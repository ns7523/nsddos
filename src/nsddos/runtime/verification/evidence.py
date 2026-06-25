"""Evidence references for verification runs."""

from __future__ import annotations

from typing import Any

from nsddos.constants import STATE_PATH
from nsddos.runtime.verification.results import VerificationEvidenceReference


def build_verification_evidence(
    context: dict[str, Any]
) -> list[VerificationEvidenceReference]:
    """Attach deterministic evidence pointers to verification execution."""
    collection = context["aggregation"].collection
    analysis = context["aggregation"].analysis
    return [
        VerificationEvidenceReference(
            "runtime_state", str(STATE_PATH), "state schema + lifecycle flags"
        ),
        VerificationEvidenceReference(
            "collection", collection.schema_version, "collection bundle schema"
        ),
        VerificationEvidenceReference(
            "analysis", analysis.schema_version, "analysis bundle schema"
        ),
        VerificationEvidenceReference(
            "reconciliation",
            analysis.reconciliation.get("detail", ""),
            "truth reconciliation",
        ),
        VerificationEvidenceReference(
            "convergence",
            analysis.convergence.get("status", "unknown"),
            "convergence state",
        ),
    ]

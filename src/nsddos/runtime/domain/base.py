"""Base typed runtime domain contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION


@dataclass(frozen=True)
class DomainModel:
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeRecord(DomainModel):
    record_id: str = ""
    record_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.payload)
        if self.record_id and "id" not in data:
            data["id"] = self.record_id
        if self.record_type and "type" not in data:
            data["type"] = self.record_type
        data.setdefault("schema_version", self.schema_version)
        data.setdefault("contract_version", self.contract_version)
        return data

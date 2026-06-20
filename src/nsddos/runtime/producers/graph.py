"""Graph producer."""

from __future__ import annotations

from nsddos.runtime.producers.collection import produce_records
from nsddos.runtime.producers.models import ProducerOutput


def produce_graph(items: list[dict]) -> ProducerOutput:
    return produce_records("graph", items)

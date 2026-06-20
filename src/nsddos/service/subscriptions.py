"""Typed service subscriptions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

SubscriptionKind = Literal["query", "replay", "convergence", "verification", "timeline"]


@dataclass(frozen=True)
class ServiceSubscription:
    subscriber_id: str
    kind: SubscriptionKind
    replay_safe: bool = True
    deterministic: bool = True
    query_backed: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def default_subscriptions() -> list[ServiceSubscription]:
    return [
        ServiceSubscription("service.query", "query"),
        ServiceSubscription("service.replay", "replay"),
        ServiceSubscription("service.convergence", "convergence"),
        ServiceSubscription("service.verification", "verification"),
        ServiceSubscription("service.timeline", "timeline"),
    ]

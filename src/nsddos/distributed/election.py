"""Deterministic leader election."""

from __future__ import annotations

from nsddos.distributed.contracts import ClusterNode, LeaderState

_STATE_PRIORITY = {
    "healthy": 4,
    "recovering": 3,
    "degraded": 2,
    "failed": 1,
}


def elect_leaders(nodes: tuple[ClusterNode, ...], election_timeout_seconds: int = 5) -> LeaderState:
    """Elect primary and standby leaders deterministically."""
    ranked = sorted(
        nodes,
        key=lambda node: (
            -_STATE_PRIORITY.get(node.state, 0),
            -node.capability_score,
            node.node_id,
        ),
    )
    primary = ranked[0].node_id if ranked else ""
    standby = ranked[1].node_id if len(ranked) > 1 else ""
    return LeaderState(
        primary_node=primary,
        standby_node=standby,
        election_timeout_seconds=election_timeout_seconds,
        re_election_required=bool(ranked and ranked[0].state == "failed"),
    )

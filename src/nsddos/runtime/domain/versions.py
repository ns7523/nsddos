"""Domain schema and contract versions."""

from __future__ import annotations

SCHEMA_VERSION = "1.0"
CONTRACT_VERSION = "17.0"
REPLAY_COMPATIBILITY = "1.x"
MIGRATION_METADATA = {
    "contract": CONTRACT_VERSION,
    "schema": SCHEMA_VERSION,
    "replay_compatibility": REPLAY_COMPATIBILITY,
}

"""Shared world state.

Concurrency rules:
* All writes run inside BEGIN IMMEDIATE transactions (serialized by SQLite).
* Every key carries a `version`. Callers may pass `expected_version`; if the
  stored version differs the write is rejected with 409 Conflict instead of
  silently overwriting a newer change (optimistic concurrency).
* Every change is appended to `world_chronicle` (audit trail).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..core.errors import Conflict, InvalidAction, NotFound
from ..database.db import transaction, utcnow
from .ownership import owned_character
from ..systems.game_data import DEFENSE_MAX, FORTIFY_AMOUNT, LOCATIONS


def record(conn: sqlite3.Connection, character_id: int | None, actor_name: str | None,
           event_type: str, description: str, key: str | None = None,
           old: Any = None, new: Any = None) -> None:
    """Append a chronicle entry. Must be called inside an open transaction."""
    conn.execute(
        """INSERT INTO world_chronicle
           (occurred_at, character_id, actor_name, event_type, state_key, old_value, new_value, description)
           VALUES (?,?,?,?,?,?,?,?)""",
        (utcnow(), character_id, actor_name, event_type, key,
         None if old is None else json.dumps(old), None if new is None else json.dumps(new), description),
    )


def _state_row(conn: sqlite3.Connection, key: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM world_state WHERE key = ?", (key,)).fetchone()
    if not row:
        raise NotFound(f"Unknown world state '{key}'.")
    return row


def get_value(conn: sqlite3.Connection, key: str) -> Any:
    return json.loads(_state_row(conn, key)["value"])


def get_state(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute("SELECT * FROM world_state ORDER BY key").fetchall()
    return {r["key"]: {"value": json.loads(r["value"]), "version": r["version"],
                       "updated_at": r["updated_at"]} for r in rows}


def set_value(conn: sqlite3.Connection, key: str, new_value: Any, *, character_id: int | None,
              actor_name: str | None, description: str, event_type: str = "world_change",
              expected_version: int | None = None) -> dict:
    """Versioned write. Must be called inside an open transaction."""
    row = _state_row(conn, key)
    if expected_version is not None and row["version"] != expected_version:
        raise Conflict(f"World state '{key}' changed (now v{row['version']}); reload and try again.")
    old_value = json.loads(row["value"])
    cur = conn.execute(
        """UPDATE world_state SET value = ?, version = version + 1, updated_at = ?, updated_by_character_id = ?
           WHERE key = ? AND version = ?""",
        (json.dumps(new_value), utcnow(), character_id, key, row["version"]),
    )
    if cur.rowcount != 1:  # defensive: cannot happen under BEGIN IMMEDIATE
        raise Conflict(f"World state '{key}' changed concurrently.")
    record(conn, character_id, actor_name, event_type, description, key, old_value, new_value)
    return {"key": key, "value": new_value, "version": row["version"] + 1}


def update_value(conn: sqlite3.Connection, key: str, new_value: Any, *, expected_version: int,
                 character_id: int | None = None, actor_name: str | None = None,
                 description: str = "") -> dict:
    """Standalone optimistic update (own transaction)."""
    with transaction(conn):
        return set_value(conn, key, new_value, character_id=character_id, actor_name=actor_name,
                         description=description or f"{key} changed", expected_version=expected_version)


def fortify(conn: sqlite3.Connection, character_id: int, account_id: int,
            expected_version: int | None = None) -> dict:
    """A character reinforces Ashenhold's walls (a shared-world change)."""
    with transaction(conn):
        character = owned_character(conn, character_id, account_id)
        if not LOCATIONS[character["location_id"]]["can_fortify"]:
            raise InvalidAction("You must be in Ashenhold to reinforce its defenses.")
        current = get_value(conn, "ashenhold_defense")
        if current >= DEFENSE_MAX:
            raise InvalidAction("Ashenhold's defenses are already at full strength.")
        new = min(DEFENSE_MAX, current + FORTIFY_AMOUNT)
        return set_value(conn, "ashenhold_defense", new, character_id=character["id"],
                         actor_name=character["name"], event_type="fortify",
                         description=f"{character['name']} reinforced Ashenhold's walls ({current} → {new}).",
                         expected_version=expected_version)


def chronicle(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute("SELECT * FROM world_chronicle ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r["id"], "occurred_at": r["occurred_at"], "actor_name": r["actor_name"],
             "event_type": r["event_type"], "description": r["description"]} for r in rows]

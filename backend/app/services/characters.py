"""Character state. Every write is scoped to one character id AND checked
against the owning account, so one character can never modify another."""
from __future__ import annotations

import sqlite3

from ..core.errors import Conflict, InvalidAction
from ..database.db import transaction, utcnow
from ..systems.game_data import CLASSES, ITEMS, LOCATIONS, STARTING_LOCATION
from . import world
from .ownership import character_row as _row, owned_character as owned_row


def _out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "name": row["name"], "class_id": row["class_id"],
        "class_name": CLASSES[row["class_id"]]["name"], "level": row["level"],
        "experience": row["experience"], "location_id": row["location_id"],
        "version": row["version"], "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def create(conn: sqlite3.Connection, account_id: int, name: str, class_id: str) -> dict:
    if class_id not in CLASSES:
        raise InvalidAction(f"Unknown class '{class_id}'.")
    now = utcnow()
    with transaction(conn):
        if conn.execute("SELECT 1 FROM characters WHERE name = ?", (name,)).fetchone():
            raise Conflict(f"A character named '{name}' already exists in this world.")
        cur = conn.execute(
            """INSERT INTO characters (account_id, name, class_id, location_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?)""",
            (account_id, name, class_id, STARTING_LOCATION, now, now),
        )
        row = _row(conn, cur.lastrowid)
        world.record(conn, row["id"], name, "character_arrived",
                     f"{name} the {CLASSES[class_id]['name']} arrives in Ashenhold.")
    return _out(row)


def list_for_account(conn: sqlite3.Connection, account_id: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM characters WHERE account_id = ? ORDER BY id",
                        (account_id,)).fetchall()
    return [_out(r) for r in rows]


def roster(conn: sqlite3.Connection) -> list[dict]:
    """Public view of every adventurer in the shared world (no private data)."""
    rows = conn.execute("SELECT id, name, class_id, level, location_id FROM characters ORDER BY id")
    return [{"id": r["id"], "name": r["name"], "class_name": CLASSES[r["class_id"]]["name"],
             "level": r["level"], "location_id": r["location_id"]} for r in rows]


def get(conn: sqlite3.Connection, character_id: int, account_id: int) -> dict:
    return _out(owned_row(conn, character_id, account_id))


def select(conn: sqlite3.Connection, token_hash: str, character_id: int, account_id: int) -> dict:
    with transaction(conn):
        row = owned_row(conn, character_id, account_id)
        conn.execute("UPDATE sessions SET selected_character_id = ?, last_seen_at = ? WHERE token_hash = ?",
                     (character_id, utcnow(), token_hash))
    return _out(row)


def _bump(conn: sqlite3.Connection, row: sqlite3.Row, expected_version: int | None, **fields) -> None:
    if expected_version is not None and row["version"] != expected_version:
        raise Conflict("Character was changed elsewhere; reload and try again.")
    sets = ", ".join(f"{k} = ?" for k in fields)
    cur = conn.execute(
        f"UPDATE characters SET {sets}, version = version + 1, updated_at = ? WHERE id = ? AND version = ?",
        (*fields.values(), utcnow(), row["id"], row["version"]),
    )
    if cur.rowcount != 1:
        raise Conflict("Character was changed elsewhere; reload and try again.")


def travel(conn: sqlite3.Connection, character_id: int, account_id: int, location_id: str,
           expected_version: int | None = None) -> dict:
    loc = LOCATIONS.get(location_id)
    if not loc:
        raise InvalidAction(f"Unknown location '{location_id}'.")
    with transaction(conn):
        row = owned_row(conn, character_id, account_id)
        if row["location_id"] == location_id:
            raise InvalidAction(f"Already in {loc['name']}.")
        if loc["requires"]:
            key, minimum = loc["requires"]
            if world.get_value(conn, key) < minimum:
                raise InvalidAction(f"{loc['name']} is too dangerous until Ashenhold's defenses reach {minimum}.")
        _bump(conn, row, expected_version, location_id=location_id)
        row = _row(conn, character_id)
    return _out(row)


def gather(conn: sqlite3.Connection, character_id: int, account_id: int) -> dict:
    with transaction(conn):
        row = owned_row(conn, character_id, account_id)
        item_id = LOCATIONS[row["location_id"]]["gather"]
        if not item_id:
            raise InvalidAction("There is nothing to gather here.")
        conn.execute(
            """INSERT INTO character_inventory (character_id, item_id, quantity) VALUES (?,?,1)
               ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + 1""",
            (character_id, item_id),
        )
        _bump(conn, row, None, experience=row["experience"] + 1)
    return {"item_id": item_id, "item_name": ITEMS[item_id]["name"],
            "inventory": inventory(conn, character_id, account_id)}


def inventory(conn: sqlite3.Connection, character_id: int, account_id: int) -> list[dict]:
    owned_row(conn, character_id, account_id)
    rows = conn.execute("SELECT item_id, quantity FROM character_inventory WHERE character_id = ? ORDER BY item_id",
                        (character_id,)).fetchall()
    return [{"item_id": r["item_id"], "name": ITEMS.get(r["item_id"], {}).get("name", r["item_id"]),
             "quantity": r["quantity"]} for r in rows]

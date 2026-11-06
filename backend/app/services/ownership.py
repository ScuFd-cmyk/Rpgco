"""Ownership checks shared by services. Knowing a character id never grants
control: the requesting account must own the character."""
from __future__ import annotations

import sqlite3

from ..core.errors import Forbidden, NotFound


def character_row(conn: sqlite3.Connection, character_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
    if not row:
        raise NotFound(f"Character {character_id} does not exist.")
    return row


def owned_character(conn: sqlite3.Connection, character_id: int, account_id: int) -> sqlite3.Row:
    row = character_row(conn, character_id)
    if row["account_id"] != account_id:
        raise Forbidden("You do not control that character.")
    return row

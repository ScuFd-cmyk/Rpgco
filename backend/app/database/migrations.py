"""Schema versioning.

The schema version is stored in SQLite's `PRAGMA user_version`. Each entry in
MIGRATIONS upgrades the schema by exactly one version and runs in its own
transaction. Never edit a released migration; append a new one instead.
"""
from __future__ import annotations

import sqlite3

MIGRATIONS: list[str] = [
    # ---- v1: Checkpoint 1 foundation -----------------------------------
    """
    CREATE TABLE accounts (
        id            INTEGER PRIMARY KEY,
        username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
        pass_salt     BLOB NOT NULL,
        pass_hash     BLOB NOT NULL,
        created_at    TEXT NOT NULL
    );

    CREATE TABLE characters (
        id            INTEGER PRIMARY KEY,
        account_id    INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        name          TEXT NOT NULL UNIQUE COLLATE NOCASE,
        class_id      TEXT NOT NULL,
        level         INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
        experience    INTEGER NOT NULL DEFAULT 0 CHECK (experience >= 0),
        location_id   TEXT NOT NULL,
        version       INTEGER NOT NULL DEFAULT 1,
        created_at    TEXT NOT NULL,
        updated_at    TEXT NOT NULL
    );
    CREATE INDEX idx_characters_account ON characters(account_id);

    CREATE TABLE sessions (
        token_hash            TEXT PRIMARY KEY,
        account_id            INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        selected_character_id INTEGER REFERENCES characters(id) ON DELETE SET NULL,
        created_at            TEXT NOT NULL,
        last_seen_at          TEXT NOT NULL
    );

    CREATE TABLE character_inventory (
        id            INTEGER PRIMARY KEY,
        character_id  INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
        item_id       TEXT NOT NULL,
        quantity      INTEGER NOT NULL CHECK (quantity > 0),
        UNIQUE (character_id, item_id)
    );

    -- Shared world: independent of any character. `version` enables
    -- optimistic concurrency so stale writes are rejected, not lost.
    CREATE TABLE world_state (
        key                     TEXT PRIMARY KEY,
        value                   TEXT NOT NULL,           -- JSON
        version                 INTEGER NOT NULL DEFAULT 1,
        updated_at              TEXT NOT NULL,
        updated_by_character_id INTEGER REFERENCES characters(id) ON DELETE SET NULL
    );

    -- Append-only audit trail of every shared-world change.
    CREATE TABLE world_chronicle (
        id            INTEGER PRIMARY KEY,
        occurred_at   TEXT NOT NULL,
        character_id  INTEGER REFERENCES characters(id) ON DELETE SET NULL,
        actor_name    TEXT,
        event_type    TEXT NOT NULL,
        state_key     TEXT,
        old_value     TEXT,
        new_value     TEXT,
        description   TEXT NOT NULL
    );

    INSERT INTO world_state (key, value, updated_at) VALUES
        ('ashenhold_defense', '0',        strftime('%Y-%m-%dT%H:%M:%S+00:00','now')),
        ('ashenhold_status',  '"secure"', strftime('%Y-%m-%dT%H:%M:%S+00:00','now'));
    INSERT INTO world_chronicle (occurred_at, event_type, description) VALUES
        (strftime('%Y-%m-%dT%H:%M:%S+00:00','now'), 'world_created',
         'The Shattered Marches stir. Ashenhold stands, its walls unmanned.');
    """,
]

SCHEMA_VERSION = len(MIGRATIONS)


def current_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn: sqlite3.Connection) -> int:
    version = current_version(conn)
    if version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema v{version} is newer than this code (v{SCHEMA_VERSION})."
        )
    for target in range(version + 1, SCHEMA_VERSION + 1):
        sql = MIGRATIONS[target - 1]
        try:
            conn.executescript(f"BEGIN IMMEDIATE;\n{sql}\nPRAGMA user_version = {target};\nCOMMIT;")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    return current_version(conn)

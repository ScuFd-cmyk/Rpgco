"""SQLite connection and transaction helpers.

Only the backend process opens the database file. Every request gets its own
connection; writes go through `transaction()` which takes SQLite's write lock
up-front (BEGIN IMMEDIATE) so read-modify-write sequences cannot interleave.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # isolation_level=None -> we control BEGIN/COMMIT explicitly.
    conn = sqlite3.connect(db_path, isolation_level=None, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = FULL")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def integrity_ok(conn: sqlite3.Connection) -> bool:
    return conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

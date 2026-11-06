from __future__ import annotations

import sqlite3

from ..core import security
from ..core.errors import Conflict, Unauthorized
from ..database.db import transaction, utcnow


def _account_out(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "username": row["username"], "created_at": row["created_at"]}


def _issue_session(conn: sqlite3.Connection, account_id: int) -> str:
    token = security.new_token()
    now = utcnow()
    conn.execute(
        "INSERT INTO sessions (token_hash, account_id, created_at, last_seen_at) VALUES (?,?,?,?)",
        (security.hash_token(token), account_id, now, now),
    )
    return token


def register(conn: sqlite3.Connection, username: str, passphrase: str) -> tuple[dict, str]:
    salt, digest = security.hash_passphrase(passphrase)
    with transaction(conn):
        if conn.execute("SELECT 1 FROM accounts WHERE username = ?", (username,)).fetchone():
            raise Conflict(f"Username '{username}' is already taken.")
        cur = conn.execute(
            "INSERT INTO accounts (username, pass_salt, pass_hash, created_at) VALUES (?,?,?,?)",
            (username, salt, digest, utcnow()),
        )
        token = _issue_session(conn, cur.lastrowid)
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _account_out(row), token


def login(conn: sqlite3.Connection, username: str, passphrase: str) -> tuple[dict, str]:
    row = conn.execute("SELECT * FROM accounts WHERE username = ?", (username,)).fetchone()
    if not row or not security.verify_passphrase(passphrase, row["pass_salt"], row["pass_hash"]):
        raise Unauthorized("Unknown username or wrong passphrase.")
    with transaction(conn):
        token = _issue_session(conn, row["id"])
    return _account_out(row), token


def logout(conn: sqlite3.Connection, token: str) -> None:
    with transaction(conn):
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (security.hash_token(token),))


def resolve_session(conn: sqlite3.Connection, token: str) -> sqlite3.Row:
    """Return the session row (joined with account) for a bearer token."""
    row = conn.execute(
        """SELECT s.token_hash, s.selected_character_id, a.id AS account_id, a.username, a.created_at
           FROM sessions s JOIN accounts a ON a.id = s.account_id WHERE s.token_hash = ?""",
        (security.hash_token(token),),
    ).fetchone()
    if not row:
        raise Unauthorized("Session is invalid or has expired. Please log in.")
    return row

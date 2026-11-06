from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterator

from fastapi import Depends, Header, Request

from ..core.errors import Unauthorized
from ..database.db import connect
from ..services import accounts


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


@dataclass
class Session:
    token: str
    token_hash: str
    account_id: int
    username: str
    selected_character_id: int | None


def current_session(authorization: str | None = Header(default=None),
                    conn: sqlite3.Connection = Depends(get_db)) -> Session:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Missing bearer token. Log in first.")
    token = authorization.split(" ", 1)[1].strip()
    row = accounts.resolve_session(conn, token)
    return Session(token, row["token_hash"], row["account_id"], row["username"], row["selected_character_id"])

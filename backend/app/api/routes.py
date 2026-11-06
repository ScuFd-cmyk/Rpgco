"""HTTP routes. Thin layer: validate input, check session, call services."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from ..schemas.api import CharacterCreate, Credentials, TravelRequest, WorldAction
from ..services import accounts, characters, world
from ..systems.game_data import CLASSES, LOCATIONS
from .deps import Session, current_session, get_db

router = APIRouter(prefix="/api")
DB = Depends(get_db)
AUTH = Depends(current_session)


# ---- accounts & sessions ------------------------------------------------
@router.post("/accounts", status_code=201)
def register(body: Credentials, conn: sqlite3.Connection = DB):
    account, token = accounts.register(conn, body.username, body.passphrase)
    return {"account": account, "token": token}


@router.post("/sessions")
def login(body: Credentials, conn: sqlite3.Connection = DB):
    account, token = accounts.login(conn, body.username, body.passphrase)
    return {"account": account, "token": token}


@router.delete("/sessions", status_code=204)
def logout(s: Session = AUTH, conn: sqlite3.Connection = DB):
    accounts.logout(conn, s.token)


@router.get("/me")
def me(s: Session = AUTH):
    return {"account_id": s.account_id, "username": s.username,
            "selected_character_id": s.selected_character_id}


# ---- static game data ---------------------------------------------------
@router.get("/meta")
def meta():
    return {"classes": CLASSES,
            "locations": {k: {key: v[key] for key in ("name", "kind", "description")}
                          | {"requires": v["requires"]} for k, v in LOCATIONS.items()}}


# ---- characters ---------------------------------------------------------
@router.post("/characters", status_code=201)
def create_character(body: CharacterCreate, s: Session = AUTH, conn: sqlite3.Connection = DB):
    return characters.create(conn, s.account_id, body.name.strip(), body.class_id)


@router.get("/characters")
def list_characters(s: Session = AUTH, conn: sqlite3.Connection = DB):
    return characters.list_for_account(conn, s.account_id)


@router.get("/characters/{character_id}")
def get_character(character_id: int, s: Session = AUTH, conn: sqlite3.Connection = DB):
    return characters.get(conn, character_id, s.account_id)


@router.post("/characters/{character_id}/select")
def select_character(character_id: int, s: Session = AUTH, conn: sqlite3.Connection = DB):
    return characters.select(conn, s.token_hash, character_id, s.account_id)


@router.post("/characters/{character_id}/travel")
def travel(character_id: int, body: TravelRequest, s: Session = AUTH, conn: sqlite3.Connection = DB):
    return characters.travel(conn, character_id, s.account_id, body.location_id, body.expected_version)


@router.post("/characters/{character_id}/gather")
def gather(character_id: int, s: Session = AUTH, conn: sqlite3.Connection = DB):
    return characters.gather(conn, character_id, s.account_id)


@router.get("/characters/{character_id}/inventory")
def inventory(character_id: int, s: Session = AUTH, conn: sqlite3.Connection = DB):
    return characters.inventory(conn, character_id, s.account_id)


# ---- shared world -------------------------------------------------------
@router.get("/world")
def get_world(s: Session = AUTH, conn: sqlite3.Connection = DB):
    return {"state": world.get_state(conn), "adventurers": characters.roster(conn)}


@router.post("/world/actions")
def world_action(body: WorldAction, s: Session = AUTH, conn: sqlite3.Connection = DB):
    # `action` is validated by the schema; only "fortify" exists in Checkpoint 1.
    return world.fortify(conn, body.character_id, s.account_id, body.expected_version)


@router.get("/chronicle")
def get_chronicle(limit: int = Query(50, ge=1, le=500), s: Session = AUTH, conn: sqlite3.Connection = DB):
    return world.chronicle(conn, limit)

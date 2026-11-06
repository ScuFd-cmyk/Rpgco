# Development log

## 2026-11-06 — Checkpoint 1: Local Foundation — COMPLETE (verified)

**Starting point:** empty git repository; no prior implementation.

**Implemented**
* FastAPI app with app factory, lifespan-managed migrations and backups (`backend/app/main.py`).
* SQLite schema v1 with `PRAGMA user_version` migrations: accounts, sessions, characters, character_inventory, world_state, world_chronicle.
* Account/passphrase auth with hashed bearer sessions; ownership checks on every character action.
* Characters: create (Sentinel/Arcanist/Ranger), list, select, travel, gather (server-validated), inventory.
* Shared world: Ashenhold defenses (`fortify`), versioned writes with 409 on stale updates, audit chronicle; Hollow Bastion is unlocked once defenses ≥ 50 (first world-state consequence).
* Backups: online backup API, integrity check, retention, protected pre-restore snapshots; startup / periodic / shutdown backups; `scripts/backup.py`, `scripts/restore.py`.
* Browser client: main menu (login/register), character select/create, world view, inventory, adventurers, chronicle, 5 s polling.

**Tests executed:** `python3 -m pytest backend/tests -q` → **14 passed**.
A character separation · B inventory separation · C shared world · D restart persistence · E backup/restore (+ retention, corrupt-backup rejection) · F concurrent fortify (2 threads, no lost updates), stale-version 409, 4-thread optimistic retry counter · ownership 403 · 401 without session · validation.

**Manual verification:** Real uvicorn server + two Playwright browser contexts (two accounts): B saw A's defense changes and location, inventories stayed separate, no console errors, mobile layout OK. Then stopped server → damaged DB → `restore.py` → restarted → data recovered.

**Known issues / limitations**
* Sessions never expire; no password reset (if a passphrase is forgotten, the account is unrecoverable without DB editing).
* Updates arrive by 5 s polling, not push.
* `restore.py` cannot detect whether the server is still running; it asks for confirmation.
* Party tables, world events, combat and progression are not built yet (by design).

**Next:** Checkpoint 2 — character systems (attributes, XP/levels, skills, equipment) as migration v2.

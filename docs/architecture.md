# Architecture (Checkpoint 1)

```
browser (frontend/)  --HTTP/JSON-->  FastAPI (backend/app)  -->  SQLite (data/world.sqlite3)
```
| Layer | Location | Responsibility |
|---|---|---|
| Client | `frontend/` | Renders server state; never decides outcomes. Polls every 5 s to see the partner's changes. |
| Routes | `app/api/` | Input validation (`schemas/`), session resolution, call services. |
| Services | `app/services/` | Game rules + transactions. `accounts`, `characters`, `world`, `ownership`. |
| Game data | `app/systems/game_data.py` | Data-driven classes, locations, items. |
| Persistence | `app/database/` | Connections, migrations, backup/restore. |

## State separation
* **Character state** — `characters`, `character_inventory`. Every write is `WHERE id = ?` and ownership-checked against the session's account.
* **World state** — `world_state` (key → JSON value + `version`) and `world_chronicle` (append-only audit). No foreign key from world rows to a required character.
* **Party state** — deferred to Checkpoint 3/6 (new migration will add `parties`, `party_members`).

## Ownership & auth
Accounts have a username + PBKDF2-hashed passphrase. Login issues a random bearer token; only its SHA-256 is stored (`sessions`). Every character endpoint checks `character.account_id == session.account_id` (403 otherwise). `core/security.py` is isolated so hosted auth can replace it.

## Consistency & concurrency
* SQLite in WAL mode, `synchronous=FULL`, `foreign_keys=ON`, 15 s busy timeout.
* Writes use `BEGIN IMMEDIATE`, so read-modify-write sequences are serialized — concurrent "fortify" calls are all counted.
* Optimistic concurrency: world keys and characters carry `version`. Clients send `expected_version`; a stale write returns **409** instead of overwriting. The UI refreshes on 409.
* Every world change appends a chronicle row (who, old → new, when).

## Schema versioning
`database/migrations.py` holds an ordered list; version is `PRAGMA user_version`. Startup applies pending migrations in transactions and refuses a DB newer than the code. Append migrations; never edit released ones.

## Offline safety
There are no timers. The world only changes through deliberate player actions.

## Decisions / deviations from blueprint
* API lives under `/api/...` so the same server can host the frontend at `/`.
* `GET /inventory/{id}` → `GET /api/characters/{id}/inventory` (nested, ownership-checked).
* `world_chronicle` is the audit table; `world_events`, `zone_state`, `vendor_inventory`, combat and party tables are deferred to their checkpoints rather than created empty.
* Only one shared-world action (`fortify`) exists; arbitrary world writes are deliberately not exposed to the browser.

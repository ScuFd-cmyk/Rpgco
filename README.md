# The Shattered Marches — MMORPG prototype

A small, persistent, browser-based shared world for two (or one) players.
Python/FastAPI backend owns a SQLite database; the browser is a thin client.

**Status:** Checkpoint 1 (Local Foundation) — implemented and tested. See `docs/development-log.md`.

## Quick start
```bash
pip install -r backend/requirements.txt
./scripts/run.sh                 # or: python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
Open http://localhost:8000. Your partner opens `http://<your-computer-LAN-IP>:8000`.
Tests: `python3 -m pytest backend/tests -q`

Docs: [setup](docs/setup.md) · [architecture](docs/architecture.md) · [API](docs/api.md) · [dev log](docs/development-log.md)

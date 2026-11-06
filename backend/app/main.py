"""Application entry point.

Run from the project root:  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .core.config import Settings, load_settings
from .core.errors import GameError
from .database import backup
from .database.db import connect, integrity_ok
from .database.migrations import migrate

log = logging.getLogger("rpgco")


def init_database(settings: Settings) -> int:
    conn = connect(settings.db_path)
    try:
        if not integrity_ok(conn):
            raise RuntimeError(f"{settings.db_path} failed integrity check. Restore a backup (scripts/restore.py).")
        return migrate(conn)
    finally:
        conn.close()


def _safe_backup(settings: Settings, label: str) -> None:
    try:
        path = backup.create_backup(settings.db_path, settings.backup_dir, label, settings.backup_retention)
        log.info("Backup written: %s", path)
    except Exception:  # a failed backup must never take the game down
        log.exception("Automatic backup (%s) failed", label)


async def _periodic_backups(settings: Settings) -> None:
    while True:
        await asyncio.sleep(settings.backup_interval_minutes * 60)
        await asyncio.to_thread(_safe_backup, settings, "auto")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        existed = settings.db_path.exists()
        version = init_database(settings)
        log.info("Database ready at %s (schema v%s)", settings.db_path, version)
        if existed:
            _safe_backup(settings, "startup")
        task = None
        if settings.backup_interval_minutes > 0:
            task = asyncio.create_task(_periodic_backups(settings))
        yield
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        _safe_backup(settings, "shutdown")

    app = FastAPI(title="Shattered Marches", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    @app.exception_handler(GameError)
    async def game_error(_: Request, exc: GameError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(sqlite3.OperationalError)
    async def db_busy(_: Request, exc: sqlite3.OperationalError):
        log.exception("Database operation failed")
        return JSONResponse(status_code=503, content={"detail": "The world is busy; please retry."})

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    app.include_router(router)
    if settings.frontend_dir.exists():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    return app


app = create_app()

"""Backup, retention and restore.

Backups use SQLite's online backup API, which produces a consistent snapshot
even while the server is running (WAL mode). Restores must be done with the
server stopped (see scripts/restore.py)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .db import connect, integrity_ok

PREFIX = "world-"
SUFFIX = ".sqlite3"
PROTECTED_LABELS = ("pre-restore",)  # never pruned automatically


def _copy(src_path: Path, dest_path: Path) -> None:
    src = sqlite3.connect(src_path)
    dest = sqlite3.connect(dest_path)
    try:
        src.backup(dest)
    finally:
        dest.close()
        src.close()


def check_file(path: Path) -> bool:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return integrity_ok(conn)
    except sqlite3.DatabaseError:
        return False
    finally:
        conn.close()


def create_backup(db_path: Path, backup_dir: Path, label: str = "manual",
                  retain: int | None = 20) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"No database at {db_path}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest = backup_dir / f"{PREFIX}{stamp}-{label}{SUFFIX}"
    _copy(db_path, dest)
    if not check_file(dest):
        dest.unlink(missing_ok=True)
        raise RuntimeError("Backup failed integrity check; it was discarded.")
    if retain:
        prune(backup_dir, retain)
    return dest


def list_backups(backup_dir: Path) -> list[Path]:
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob(f"{PREFIX}*{SUFFIX}"))  # timestamp sorts lexically


def prune(backup_dir: Path, retain: int) -> None:
    rotating = [p for p in list_backups(backup_dir)
                if not any(p.stem.endswith(lbl) for lbl in PROTECTED_LABELS)]
    for old in rotating[:-retain] if len(rotating) > retain else []:
        old.unlink(missing_ok=True)


def restore_backup(backup_path: Path, db_path: Path, backup_dir: Path) -> Path | None:
    """Replace the live database contents with `backup_path`.

    The current database is first saved as a protected 'pre-restore' backup so
    a restore can itself be undone. Returns that safety backup's path."""
    if not backup_path.exists():
        raise FileNotFoundError(backup_path)
    if not check_file(backup_path):
        raise RuntimeError(f"Backup {backup_path} failed integrity check; not restoring.")
    safety = None
    if db_path.exists():
        safety = create_backup(db_path, backup_dir, label="pre-restore", retain=None)
    dest = connect(db_path)  # opens in WAL mode so the copy lands consistently
    src = sqlite3.connect(backup_path)
    try:
        src.backup(dest)
        if not integrity_ok(dest):
            raise RuntimeError("Restored database failed integrity check.")
    finally:
        src.close()
        dest.close()
    return safety

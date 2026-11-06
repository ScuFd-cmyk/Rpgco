"""Runtime configuration. Values come from environment variables so that
source code never hard-codes machine-specific paths or secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    backup_dir: Path
    frontend_dir: Path
    backup_retention: int = 20
    backup_interval_minutes: int = 30  # 0 disables periodic backups

    @property
    def db_path(self) -> Path:
        return self.data_dir / "world.sqlite3"


def load_settings() -> Settings:
    return Settings(
        data_dir=Path(os.environ.get("RPG_DATA_DIR", PROJECT_ROOT / "data")),
        backup_dir=Path(os.environ.get("RPG_BACKUP_DIR", PROJECT_ROOT / "backups")),
        frontend_dir=Path(os.environ.get("RPG_FRONTEND_DIR", PROJECT_ROOT / "frontend")),
        backup_retention=int(os.environ.get("RPG_BACKUP_RETENTION", "20")),
        backup_interval_minutes=int(os.environ.get("RPG_BACKUP_INTERVAL_MINUTES", "30")),
    )

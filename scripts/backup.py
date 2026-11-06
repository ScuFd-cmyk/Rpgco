"""Create a database backup now.  Usage: python scripts/backup.py [label]
Safe to run while the server is running."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.core.config import load_settings  # noqa: E402
from backend.app.database.backup import create_backup  # noqa: E402

s = load_settings()
label = sys.argv[1] if len(sys.argv) > 1 else "manual"
print(create_backup(s.db_path, s.backup_dir, label, s.backup_retention))

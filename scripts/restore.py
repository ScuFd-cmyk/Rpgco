"""List or restore backups.  STOP THE SERVER FIRST.

  python scripts/restore.py            # list backups (newest last)
  python scripts/restore.py latest     # restore the newest backup
  python scripts/restore.py <file>     # restore a specific backup

The current database is saved as a '-pre-restore' backup before it is replaced."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.core.config import load_settings  # noqa: E402
from backend.app.database.backup import check_file, list_backups, restore_backup  # noqa: E402

s = load_settings()
backups = list_backups(s.backup_dir)
if len(sys.argv) < 2:
    for i, p in enumerate(backups):
        print(f"{i:3d}  {p.name}  ({p.stat().st_size // 1024} KiB, {'ok' if check_file(p) else 'CORRUPT'})")
    print(f"\n{len(backups)} backup(s) in {s.backup_dir}")
    sys.exit(0)

target = backups[-1] if sys.argv[1] == "latest" and backups else Path(sys.argv[1])
if sys.argv[1] != "latest" and not target.is_absolute() and not target.exists():
    target = s.backup_dir / sys.argv[1]
if input(f"Restore {target.name} over {s.db_path}? Is the server stopped? [y/N] ").strip().lower() != "y":
    sys.exit("Cancelled.")
safety = restore_backup(target, s.db_path, s.backup_dir)
print(f"Restored {target.name}.")
if safety:
    print(f"Previous database saved as {safety.name}")

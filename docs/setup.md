# Setup, launch, backup & restore

## Requirements
Python 3.12+ (tested on 3.13). From the project root:
```bash
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

## Launch
```bash
./scripts/run.sh            # Windows: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
* You: http://localhost:8000
* Partner on the same Wi-Fi: `http://<host LAN IP>:8000` (find it with `ipconfig` / `ip addr`). Allow Python through the firewall if asked.
* Each player creates their **own account** (username + passphrase), then their characters.
* Never put `data/world.sqlite3` on a shared network drive — only the server process opens it.

## Configuration (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| `RPG_DATA_DIR` | `data/` | Where `world.sqlite3` lives |
| `RPG_BACKUP_DIR` | `backups/` | Backup folder |
| `RPG_BACKUP_RETENTION` | `20` | Rotating backups kept (pre-restore backups are never pruned) |
| `RPG_BACKUP_INTERVAL_MINUTES` | `30` | Periodic backup while running; `0` disables |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | `run.sh` bind address |

## Saving
Every game action is written to SQLite in a transaction the moment it happens — there is no "save" button and nothing is lost on close.

## Backups
Automatic: at startup, every 30 min while running, and at shutdown. Manual (safe while running):
```bash
python3 scripts/backup.py [label]
```

## Restore
1. **Stop the server** (Ctrl+C).
2. `python3 scripts/restore.py` — lists backups with an integrity check.
3. `python3 scripts/restore.py latest` or `python3 scripts/restore.py <filename>` — confirms, saves the current DB as a `-pre-restore` backup, then restores.
4. Start the server again.

If the server refuses to start with an integrity-check error, restore the newest backup marked `ok`.

#!/usr/bin/env bash
# Start the game server. Reachable from other devices on your Wi-Fi at
# http://<this-computer's-LAN-IP>:${PORT:-8000}
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m uvicorn backend.app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"

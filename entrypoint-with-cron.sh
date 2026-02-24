#!/usr/bin/env bash
set -euo pipefail

# Ensure persistence directory and artifacts folder exist
mkdir -p /app/backend/data/artifacts

echo "Starting Open WebUI via start.sh..."
# Start Open WebUI in the background so supercronic can run as PID 1.
bash start.sh &
webui_pid=$!

echo "Starting Cortextia Index Sync Scheduler (supercronic)..."

# Forward termination signals to Open WebUI for graceful shutdown.
trap 'echo "Stopping..."; kill -TERM "$webui_pid" 2>/dev/null || true; wait "$webui_pid" 2>/dev/null || true' TERM INT

# Run supercronic in the foreground as PID 1.
exec /usr/local/bin/supercronic /etc/cron.d/sync-index.cron

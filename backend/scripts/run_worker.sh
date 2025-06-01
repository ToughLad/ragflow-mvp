#!/usr/bin/env bash
set -e

# Start RQ worker for background tasks
echo "Starting RQ worker for email, document, and digest processing..."

python - <<'PY'
from app.queue.tasks import start_worker
start_worker()
PY

#!/usr/bin/env bash
set -e

# Ensure database tables exist before starting
bash $(dirname "$0")/init_db.sh

uvicorn app.main:app --host 0.0.0.0 --port 8000

#!/bin/bash
set -e

echo "Waiting for database to be ready..."
# Simple wait loop for postgres
until python -c "
import os
import sys
from sqlalchemy import create_engine
engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://user:password@postgres:5432/autocareer'))
try:
    conn = engine.connect()
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'Database not ready: {e}')
    sys.exit(1)
" 2>/dev/null; do
  echo "Postgres is unavailable - sleeping 2s..."
  sleep 2
done

echo "Database is ready!"

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
# Use multiple workers for parallel request handling
# Note: Background tasks run in the same process, so we also use asyncio.to_thread()
# for blocking operations to avoid blocking other requests within the same worker
exec uvicorn server:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}

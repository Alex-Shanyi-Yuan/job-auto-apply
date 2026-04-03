#!/bin/bash
set -e

DB_BACKEND=${DATABASE_BACKEND:-postgres}

if [ "$DB_BACKEND" = "postgres" ]; then
  echo "Waiting for PostgreSQL to be ready..."
  # Simple wait loop for postgres
  until python -c "
import os
import sys
from sqlalchemy import create_engine
postgres_url = os.getenv('POSTGRES_DATABASE_URL') or os.getenv('DATABASE_URL') or 'postgresql://user:password@postgres:5432/autocareer'
engine = create_engine(postgres_url)
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

  echo "PostgreSQL is ready!"
else
  echo "Postgres wait skipped for DATABASE_BACKEND=$DB_BACKEND"
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
# Default to one worker because DB sync runs in lifespan startup/shutdown.
exec uvicorn server:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1}

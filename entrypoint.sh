#!/bin/sh
set -e

echo "Waiting for database..."
until pg_isready -h "${DB_HOST:-divvy-db}" -p "${DB_PORT:-5432}"; do
  sleep 1
done

echo "Running migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

#!/bin/sh
set -e

echo "⏳ Waiting for PostgreSQL to be ready..."
# На всякий случай — дополнительная пауза, если healthcheck ещё не сработал
until pg_isready -h "${DB_HOST:-db}" -U "${DB_USER:-user}" -q; do
    sleep 1
done
echo "✅ PostgreSQL is ready"

echo "🔄 Running Alembic migrations..."
alembic upgrade head
echo "✅ Migrations applied"

echo "🚀 Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

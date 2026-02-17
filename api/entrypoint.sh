#!/bin/sh
set -e

# ── Динамическое добавление группы gpio ──────────────────────────────────────
# Определяем GID группы, которой принадлежит /dev/gpiomem на хосте,
# и создаём такую же группу внутри контейнера (если ещё нет).
# Это позволяет работать с любым GID gpio — не только 997.
if [ -e /dev/gpiomem ]; then
    HOST_GPIO_GID=$(stat -c '%g' /dev/gpiomem)
    if ! getent group "$HOST_GPIO_GID" > /dev/null 2>&1; then
        echo "📌 Создаём группу gpio с GID $HOST_GPIO_GID внутри контейнера..."
        groupadd -g "$HOST_GPIO_GID" gpio_host 2>/dev/null || true
    fi
    # Добавляем текущего пользователя в эту группу
    CURRENT_USER=$(whoami)
    usermod -aG "$HOST_GPIO_GID" "$CURRENT_USER" 2>/dev/null || true
fi

echo "⏳ Waiting for PostgreSQL to be ready..."
until pg_isready -h "${DB_HOST:-db}" -U "${DB_USER:-user}" -q; do
    sleep 1
done
echo "✅ PostgreSQL is ready"

echo "🔄 Running Alembic migrations..."
alembic upgrade head
echo "✅ Migrations applied"

echo "🚀 Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

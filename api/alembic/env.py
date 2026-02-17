import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Добавляем корень проекта в sys.path, чтобы импортировать app ──────────────
# Структура: /app/alembic/env.py → /app — корень
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем Base и все модели, чтобы Alembic знал о таблицах
from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401  ← регистрирует все модели в Base.metadata

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# Читаем DATABASE_URL из переменной окружения и подставляем в конфиг
database_url = os.getenv("DATABASE_URL", "postgresql://user:password@db/greenhousedb")
config.set_main_option("sqlalchemy.url", database_url)

# Логирование из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Целевые метаданные для автогенерации миграций
target_metadata = Base.metadata


# ── Offline mode (alembic upgrade head --sql) ─────────────────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (реальное подключение к БД) ───────────────────────────────────
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,      # обнаруживать изменения типов колонок
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

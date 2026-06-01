# app/db/migrations/env.py

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from app.core.config import settings
from app.db.base import Base
from app.models.profile import Profile  # noqa: F401

# ── Alembic Config ────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Replace asyncpg (async driver) with psycopg2 (sync driver)
# Alembic runs migrations synchronously — it does not need asyncpg
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace(
        "postgresql+asyncpg", "postgresql+psycopg2"
    ),
)


# ── Offline mode ──────────────────────────────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ───────────────────────────────────────────────
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
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ───────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Alembic Config object
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Load DATABASE_URL from your Pydantic settings ---
# Note: we only use DATABASE_URL, so other env vars like BOT_TOKEN won't affect Alembic.
from config import get_settings
settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

# Inject DATABASE_URL into Alembic config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Import SQLAlchemy metadata
from db.models import metadata as target_metadata  # noqa: E402


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table="alembic_version",
        version_table_schema="public",
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Synchronous portion executed within an async connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table="alembic_version",
        version_table_schema="public",
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an AsyncEngine."""
    connectable: AsyncEngine = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
        future=True,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

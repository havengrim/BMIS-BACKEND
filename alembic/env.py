import asyncio
import selectors
import sys
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Load app config and models
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base  # noqa: F401
from app.modules.users.model import User  # noqa: F401
from app.modules.profiles.model import Profile  # noqa: F401
from app.modules.announcements.model import Announcement  # noqa: F401
from app.modules.blotter.model import BlotterReport  # noqa: F401
from app.modules.certificates.model import CertificateRequest, CertificateCounter  # noqa: F401
from app.modules.business_permits.model import BusinessPermit  # noqa: F401
from app.modules.complaints.model import Complaint  # noqa: F401
from app.modules.emergency.model import EmergencyReport, EmergencyAlert  # noqa: F401
from app.modules.chat.model import ChatMessage  # noqa: F401

# Fix for Windows: psycopg async requires SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.DefaultEventLoopPolicy()
    )
    # Force SelectorEventLoop on Windows
    selector = selectors.SelectSelector()
    loop = asyncio.SelectorEventLoop(selector)
    asyncio.set_event_loop(loop)

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url from our settings (reads from .env)
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://").replace(
        "postgres://", "postgresql+psycopg://"
    ),
)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    if sys.platform == "win32":
        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(selector)
        loop.run_until_complete(run_async_migrations())
        loop.close()
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

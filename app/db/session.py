from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

# Convert psycopg URL to async variant: postgresql+psycopg
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+psycopg://"
).replace(
    "postgres://", "postgresql+psycopg://"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,      # Reconnect on stale connections (important for AWS RDS)
    pool_recycle=1800,        # Recycle connections every 30 min — prevents RDS timeout drops
    pool_timeout=30,          # Wait max 30 s for an available connection before raising
    pool_use_lifo=True,       # Prefer recently-used connections — better for auto-scaling
    pool_reset_on_return="rollback",  # Always roll back before returning to pool
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

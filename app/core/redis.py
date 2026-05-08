from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url
from app.core.config import settings

_redis: Redis | None = None


async def init_redis() -> Redis:
    global _redis
    _redis = redis_from_url(settings.REDIS_URL, decode_responses=True)
    # Verify connection on startup
    await _redis.ping()
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def get_redis() -> Redis:
    """Sync getter — use after init_redis() has been called in lifespan."""
    if _redis is None:
        raise RuntimeError("Redis connection not initialized. Check lifespan startup.")
    return _redis


async def get_redis_dep() -> Redis:
    """FastAPI dependency — yields the shared Redis client."""
    yield get_redis()

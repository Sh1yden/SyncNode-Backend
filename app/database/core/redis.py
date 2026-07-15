"""Redis-клиент для хранения refresh-токенов."""

from redis.asyncio import ConnectionPool, Redis

from app.core import settings

_pool = ConnectionPool.from_url(settings.redis_url, decode_responses=True)


async def get_redis() -> Redis:
    """FastAPI-зависимость, отдающая Redis-клиент."""
    async with Redis(connection_pool=_pool) as client:
        yield client

from typing import Optional
from redis.asyncio import Redis
from app.core.config import settings

redis_client: Optional[Redis] = None

async def init_cache() -> None:
    global redis_client
    redis_client = Redis.from_url(settings.redis_url, encoding='utf-8', decode_responses=True)

async def close_cache() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None

async def cache_get(key: str) -> Optional[str]:
    if redis_client is None:
        await init_cache()
    return await redis_client.get(key)

async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    if redis_client is None:
        await init_cache()
    await redis_client.setex(key, ttl, value)

async def cache_delete(key: str) -> None:
    if redis_client is None:
        await init_cache()
    await redis_client.delete(key)

async def cache_delete_pattern(pattern: str) -> None:
    if redis_client is None:
        await init_cache()
    async for key in redis_client.scan_iter(match=pattern):
        await redis_client.delete(key)

import pathlib
r = pathlib.Path(__file__).resolve().parent.parent

def w(p, c):
    f = r / p
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(c, encoding='utf-8')
    print(f'  OK {p}')

# database.py
w('backend/app/core/database.py', '''from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url if hasattr(settings, 'async_database_url') else settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db() -> None:
    await engine.dispose()
''')

# cache.py
w('backend/app/core/cache.py', '''from typing import Optional
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
''')

print('Core files done!')

from collections.abc import Awaitable, Callable

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def check_postgres(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis(redis_url: str) -> bool:
    client = Redis.from_url(redis_url)
    try:
        pong = await client.ping()
        return bool(pong)
    except Exception:
        return False
    finally:
        await client.close()


async def aggregate_health(
    postgres_check: Callable[[], Awaitable[bool]],
    redis_check: Callable[[], Awaitable[bool]],
) -> dict[str, object]:
    postgres_ok = await postgres_check()
    redis_ok = await redis_check()
    status = "ok" if postgres_ok and redis_ok else "degraded"
    return {
        "status": status,
        "services": {"postgres": postgres_ok, "redis": redis_ok},
    }

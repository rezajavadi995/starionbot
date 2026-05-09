from collections.abc import Awaitable, Callable
from inspect import isawaitable

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
        pong = client.ping()
        return await _resolve_bool(pong)
    except Exception:
        return False
    finally:
        close_result = client.close()
        if isawaitable(close_result):
            await close_result


async def _resolve_bool(value: Awaitable[bool] | bool) -> bool:
    if isawaitable(value):
        resolved = await value
        return bool(resolved)
    return bool(value)


async def aggregate_health(
    postgres_check: Callable[[], Awaitable[bool]],
    redis_check: Callable[[], Awaitable[bool]],
) -> dict[str, object]:
    postgres_ok = await _resolve_bool(postgres_check())
    redis_ok = await _resolve_bool(redis_check())
    status = "ok" if postgres_ok and redis_ok else "degraded"
    return {
        "status": status,
        "services": {"postgres": postgres_ok, "redis": redis_ok},
    }

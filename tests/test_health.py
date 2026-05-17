import asyncio

from bot.services.health import aggregate_health


def test_aggregate_health_degraded() -> None:
    report = asyncio.run(
        aggregate_health(postgres_check=lambda: _false(), redis_check=lambda: _true())
    )
    assert report["status"] == "degraded"


async def _true() -> bool:
    return True


async def _false() -> bool:
    return False

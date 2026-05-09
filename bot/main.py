from fastapi import FastAPI

from bot.api.ws import router as ws_router
from bot.core.config import settings
from bot.core.logging import setup_logging
from bot.db.session import engine
from bot.services.health import aggregate_health, check_postgres, check_redis

setup_logging()
app = FastAPI(title="StarionBot API", version="0.3.0")
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict[str, object]:
    report = await aggregate_health(
        postgres_check=lambda: check_postgres(engine),
        redis_check=lambda: check_redis(settings.redis_url.get_secret_value()),
    )
    report["env"] = settings.app_env
    return report

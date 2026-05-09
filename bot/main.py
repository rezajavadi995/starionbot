from fastapi import FastAPI

from bot.core.config import settings
from bot.core.logging import setup_logging
from bot.api.ws import router as ws_router


setup_logging()
app = FastAPI(title="StarionBot API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}

app.include_router(ws_router)

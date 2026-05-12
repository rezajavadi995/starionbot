from aiogram import Bot, Dispatcher

from bot.botapp.handlers.join import router as join_router
from bot.botapp.handlers.stars import router as stars_router
from bot.botapp.handlers.start import router as start_router
from bot.core.config import settings


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(stars_router)
    dp.include_router(start_router)
    dp.include_router(join_router)
    return dp


async def run_bot() -> None:
    bot = Bot(token=settings.bot_token.get_secret_value())
    dp = build_dispatcher()
    await dp.start_polling(bot)

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from bot.core.config import settings
from bot.i18n.messages import t

router = Router(name="join")


@router.callback_query(F.data == "join:verify")
async def verify_join(callback: CallbackQuery, bot: Bot) -> None:
    member = await bot.get_chat_member(f"@{settings.mandatory_join_channel}", callback.from_user.id)
    lang = "fa"
    if member.status in {"member", "administrator", "creator"}:
        await callback.message.answer(t(lang, "join_verified"))
    else:
        await callback.message.answer(t(lang, "join_failed"))
    await callback.answer()

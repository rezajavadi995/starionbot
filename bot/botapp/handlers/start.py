from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.core.config import settings
from bot.i18n.messages import t

router = Router(name="start")

LANG_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="English", callback_data="lang:en")],
        [InlineKeyboardButton(text="فارسی", callback_data="lang:fa")],
    ]
)


def join_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Join Channel", url=f"https://t.me/{settings.mandatory_join_channel}"
                )
            ],
            [InlineKeyboardButton(text="Verify Membership", callback_data="join:verify")],
        ]
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(t("en", "choose_language"), reply_markup=LANG_KB)


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":", 1)[1]
    await callback.message.answer(t(lang, "join_required"), reply_markup=join_kb())
    await callback.answer()

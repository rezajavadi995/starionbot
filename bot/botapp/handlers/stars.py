from decimal import Decimal

from aiogram import F, Router
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy import select

from bot.core.config import settings
from bot.db.session import SessionLocal
from bot.models.user import User
from bot.services.stars import apply_successful_stars_payment, build_stars_invoice

router = Router(name="stars")


async def _get_or_create_user(telegram_id: int, full_name: str, username: str | None) -> User:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(
                telegram_id=telegram_id, full_name=full_name, username=username, language="fa"
            )
            session.add(user)
            await session.flush()
            await session.commit()
        return user


@router.message(F.text == "/addstars")
async def add_stars(message: Message) -> None:
    if not settings.stars_enabled:
        await message.answer("Telegram Stars payments are currently disabled.")
        return
    if message.from_user is None:
        return

    user = await _get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )
    invoice = build_stars_invoice(user_id=user.id, amount_xtr=Decimal("100"))
    await message.answer_invoice(
        title=str(invoice["title"]),
        description=str(invoice["description"]),
        payload=str(invoice["payload"]),
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=100)],
    )


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    if message.from_user is None or message.successful_payment is None:
        return

    user = await _get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )

    payment = message.successful_payment
    amount_xtr = Decimal(payment.total_amount)

    async with SessionLocal() as session:
        await apply_successful_stars_payment(
            session,
            user_id=user.id,
            amount_xtr=amount_xtr,
            telegram_transaction_id=payment.telegram_payment_charge_id,
            telegram_charge_id=payment.telegram_payment_charge_id,
            invoice_payload=payment.invoice_payload,
            provider_payment_charge_id=payment.provider_payment_charge_id,
        )
        await session.commit()

    await message.answer("Stars payment confirmed and your balance has been updated.")

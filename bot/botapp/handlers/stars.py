from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery

from bot.core.config import settings
from bot.db.session import SessionLocal
from bot.services.stars import (
    StarsPaymentValidationError,
    apply_successful_stars_payment,
    build_stars_invoice,
    normalize_stars_amount,
    parse_stars_invoice_payload,
    validate_successful_payment_currency,
)
from bot.services.users import get_or_create_user

router = Router(name="stars")


@router.message(F.text.regexp(r"^/start\s+addstars(?:_|\s|$).*"))
async def add_stars_from_deep_link(message: Message) -> None:
    await _send_stars_invoice_from_text(message)


@router.message(Command("addstars"))
async def add_stars(message: Message) -> None:
    await _send_stars_invoice_from_text(message)


async def _send_stars_invoice_from_text(message: Message) -> None:
    try:
        amount_xtr = _amount_from_text(message.text or "")
    except StarsPaymentValidationError as exc:
        await message.answer(str(exc))
        return
    await send_stars_invoice(message, amount_xtr=amount_xtr)


async def send_stars_invoice(message: Message, *, amount_xtr: Decimal) -> None:
    if not settings.stars_enabled:
        await message.answer("Telegram Stars payments are currently disabled.")
        return
    if message.from_user is None:
        return

    try:
        min_topup = Decimal(settings.stars_min_topup_xtr)
        if amount_xtr < min_topup:
            raise StarsPaymentValidationError(f"Minimum Stars top-up is {min_topup} XTR")
        amount_xtr = normalize_stars_amount(amount_xtr)
    except StarsPaymentValidationError as exc:
        await message.answer(str(exc))
        return

    async with SessionLocal() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
        )
        await session.commit()

    invoice = build_stars_invoice(user_id=user.id, amount_xtr=amount_xtr)
    await message.answer_invoice(
        title=str(invoice["title"]),
        description=str(invoice["description"]),
        payload=str(invoice["payload"]),
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=int(amount_xtr))],
    )


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    try:
        if pre_checkout_query.currency != "XTR":
            raise StarsPaymentValidationError("Only Telegram Stars (XTR) payments are supported")
        payload = parse_stars_invoice_payload(pre_checkout_query.invoice_payload)
        if payload.amount_xtr != Decimal(pre_checkout_query.total_amount):
            raise StarsPaymentValidationError("Invoice payload amount mismatch")
    except StarsPaymentValidationError as exc:
        await pre_checkout_query.answer(ok=False, error_message=str(exc))
        return

    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    if message.from_user is None or message.successful_payment is None:
        return

    payment = message.successful_payment
    amount_xtr = Decimal(payment.total_amount)

    try:
        validate_successful_payment_currency(payment.currency)
    except StarsPaymentValidationError as exc:
        await message.answer(str(exc))
        return

    async with SessionLocal() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
        )
        try:
            await apply_successful_stars_payment(
                session,
                user_id=user.id,
                amount_xtr=amount_xtr,
                telegram_transaction_id=payment.telegram_payment_charge_id,
                telegram_charge_id=payment.telegram_payment_charge_id,
                invoice_payload=payment.invoice_payload,
                provider_payment_charge_id=payment.provider_payment_charge_id,
            )
        except StarsPaymentValidationError as exc:
            await session.rollback()
            await message.answer(str(exc))
            return
        await session.commit()

    await message.answer("Stars payment confirmed and your balance has been updated.")


def _amount_from_text(text: str) -> Decimal:
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return Decimal("1")

    raw = parts[1].strip()
    if raw.startswith("addstars_"):
        raw = raw.removeprefix("addstars_")
    elif raw == "addstars":
        return Decimal("1")
    elif raw.startswith("addstars "):
        raw = raw.split(maxsplit=1)[1]

    try:
        return Decimal(raw)
    except ArithmeticError as exc:
        raise StarsPaymentValidationError("invalid Stars top-up amount") from exc

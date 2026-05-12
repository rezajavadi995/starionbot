from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.payment_history import PaymentHistory
from bot.models.stars import StarTransaction, UserStarBalance

MIN_STARS_TOPUP_XTR = Decimal("1")
STARS_CURRENCY = "XTR"
STARS_PROVIDER = "telegram_stars"
SUCCESS_STATUS = "succeeded"


class StarsPaymentValidationError(ValueError):
    pass


@dataclass(slots=True)
class StarsInvoicePayload:
    user_id: int
    amount_xtr: Decimal
    nonce: str


def build_stars_invoice(
    *, user_id: int, amount_xtr: Decimal, description: str = "StarionBot Stars Top-up"
) -> dict[str, object]:
    normalized_amount = normalize_stars_amount(amount_xtr)
    payload = f"stars_topup:{user_id}:{normalized_amount}:{uuid.uuid4()}"
    return {
        "title": "StarionBot Top-up",
        "description": description,
        "payload": payload,
        "currency": STARS_CURRENCY,
        "prices": [{"label": "Stars", "amount": int(normalized_amount)}],
    }


def normalize_stars_amount(amount_xtr: Decimal) -> Decimal:
    if amount_xtr != amount_xtr.to_integral_value():
        raise StarsPaymentValidationError("Telegram Stars amount must be an integer XTR value")
    if amount_xtr < MIN_STARS_TOPUP_XTR:
        raise StarsPaymentValidationError("Telegram Stars top-up minimum is 1 XTR")
    return amount_xtr


def parse_stars_invoice_payload(invoice_payload: str) -> StarsInvoicePayload:
    parts = invoice_payload.split(":")
    if len(parts) != 4 or parts[0] != "stars_topup":
        raise StarsPaymentValidationError("invalid Stars invoice payload")
    try:
        user_id = int(parts[1])
        amount_xtr = Decimal(parts[2])
    except (ValueError, ArithmeticError) as exc:
        raise StarsPaymentValidationError("invalid Stars invoice payload values") from exc
    normalize_stars_amount(amount_xtr)
    return StarsInvoicePayload(user_id=user_id, amount_xtr=amount_xtr, nonce=parts[3])


async def apply_successful_stars_payment(
    session: AsyncSession,
    *,
    user_id: int,
    amount_xtr: Decimal,
    telegram_transaction_id: str,
    telegram_charge_id: str,
    invoice_payload: str,
    provider_payment_charge_id: str | None,
) -> StarTransaction:
    if not telegram_transaction_id.strip():
        raise StarsPaymentValidationError("missing Telegram Stars transaction id")

    normalized_amount = normalize_stars_amount(amount_xtr)
    parsed_payload = parse_stars_invoice_payload(invoice_payload)
    if parsed_payload.user_id != user_id:
        raise StarsPaymentValidationError("Stars invoice payload user does not match payer")
    if parsed_payload.amount_xtr != normalized_amount:
        raise StarsPaymentValidationError("Stars invoice payload amount does not match payment")

    existing = await session.scalar(
        select(StarTransaction).where(
            StarTransaction.telegram_transaction_id == telegram_transaction_id
        )
    )
    if existing is not None:
        return existing

    balance = await session.scalar(
        select(UserStarBalance).where(UserStarBalance.user_id == user_id).with_for_update()
    )
    if balance is None:
        balance = UserStarBalance(user_id=user_id, balance=Decimal("0"))
        session.add(balance)
        await session.flush()

    balance.balance = balance.balance + normalized_amount

    tx = StarTransaction(
        user_id=user_id,
        amount_xtr=normalized_amount,
        telegram_transaction_id=telegram_transaction_id,
        telegram_charge_id=telegram_charge_id,
        invoice_payload=invoice_payload,
        provider_payment_charge_id=provider_payment_charge_id,
    )
    session.add(tx)
    await session.flush()

    history = PaymentHistory(
        user_id=user_id,
        provider=STARS_PROVIDER,
        asset="stars",
        amount=normalized_amount,
        external_transaction_id=telegram_transaction_id,
        status=SUCCESS_STATUS,
        metadata_json=json.dumps(
            {
                "telegram_charge_id": telegram_charge_id,
                "invoice_payload": invoice_payload,
                "provider_payment_charge_id": provider_payment_charge_id,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    session.add(history)
    await session.flush()
    return tx


def parse_telegram_successful_payment(update_json: str) -> dict[str, str | Decimal | None]:
    payload = json.loads(update_json)
    payment = payload["message"]["successful_payment"]
    return {
        "telegram_transaction_id": payment.get("telegram_payment_charge_id", ""),
        "telegram_charge_id": payment.get("telegram_payment_charge_id", ""),
        "provider_payment_charge_id": payment.get("provider_payment_charge_id"),
        "invoice_payload": payment["invoice_payload"],
        "amount_xtr": Decimal(payment["total_amount"]),
        "currency": payment.get("currency"),
    }


def validate_successful_payment_currency(currency: str | None) -> None:
    if currency != STARS_CURRENCY:
        raise StarsPaymentValidationError("successful payment currency is not XTR")

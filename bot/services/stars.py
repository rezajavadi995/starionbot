from __future__ import annotations

import json
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.stars import StarTransaction, UserStarBalance

MIN_STARS_TOPUP_XTR = Decimal("1")


def build_stars_invoice(
    *, user_id: int, amount_xtr: Decimal, description: str = "StarionBot Stars Top-up"
) -> dict[str, object]:
    payload = f"stars_topup:{user_id}:{uuid.uuid4()}"
    return {
        "title": "StarionBot Top-up",
        "description": description,
        "payload": payload,
        "currency": "XTR",
        "prices": [{"label": "Stars", "amount": int(amount_xtr)}],
    }


def parse_stars_invoice_payload(payload: str) -> tuple[int, str]:
    if not payload.startswith("stars_topup:"):
        raise ValueError("invalid invoice payload prefix")
    parts = payload.split(":")
    if len(parts) != 3:
        raise ValueError("invalid invoice payload format")
    user_id = int(parts[1])
    nonce = parts[2]
    if not nonce:
        raise ValueError("invalid invoice payload nonce")
    return user_id, nonce


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

    balance.balance = balance.balance + amount_xtr

    tx = StarTransaction(
        user_id=user_id,
        amount_xtr=amount_xtr,
        telegram_transaction_id=telegram_transaction_id,
        telegram_charge_id=telegram_charge_id,
        invoice_payload=invoice_payload,
        provider_payment_charge_id=provider_payment_charge_id,
    )
    session.add(tx)
    await session.flush()
    return tx


def parse_telegram_successful_payment(update_json: str) -> dict[str, str | Decimal]:
    payload = json.loads(update_json)
    payment = payload["message"]["successful_payment"]
    amount_xtr = Decimal(payment["total_amount"])
    if amount_xtr < MIN_STARS_TOPUP_XTR:
        raise ValueError("stars topup amount must be >= 1 XTR")
    if payment.get("currency") != "XTR":
        raise ValueError("invalid payment currency")
    return {
        "telegram_transaction_id": payment.get("telegram_payment_charge_id", ""),
        "telegram_charge_id": payment.get("telegram_payment_charge_id", ""),
        "provider_payment_charge_id": payment.get("provider_payment_charge_id"),
        "invoice_payload": payment["invoice_payload"],
        "amount_xtr": amount_xtr,
    }

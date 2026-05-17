import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.db.base import Base
from bot.models.payment_history import PaymentHistory
from bot.models.stars import UserStarBalance
from bot.models.user import User
from bot.services.stars import (
    StarsPaymentValidationError,
    apply_successful_stars_payment,
    build_stars_invoice,
)


def test_apply_successful_stars_payment_idempotent() -> None:
    pytest.importorskip("aiosqlite")
    asyncio.run(_scenario())


def test_stars_invoice_rejects_sub_minimum_amount() -> None:
    with pytest.raises(StarsPaymentValidationError):
        build_stars_invoice(user_id=1, amount_xtr=Decimal("0"))


async def _scenario() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        user = User(telegram_id=99111, username="stars", full_name="Stars User", language="en")
        session.add(user)
        await session.flush()

        invoice = build_stars_invoice(user_id=user.id, amount_xtr=Decimal("1"))
        tx1 = await apply_successful_stars_payment(
            session,
            user_id=user.id,
            amount_xtr=Decimal("1"),
            telegram_transaction_id="tg_tx_1",
            telegram_charge_id="tg_charge_1",
            invoice_payload=str(invoice["payload"]),
            provider_payment_charge_id="provider_1",
        )
        tx2 = await apply_successful_stars_payment(
            session,
            user_id=user.id,
            amount_xtr=Decimal("1"),
            telegram_transaction_id="tg_tx_1",
            telegram_charge_id="tg_charge_1",
            invoice_payload=str(invoice["payload"]),
            provider_payment_charge_id="provider_1",
        )
        assert tx1.id == tx2.id

        balance = await session.scalar(
            select(UserStarBalance).where(UserStarBalance.user_id == user.id)
        )
        assert balance is not None
        assert balance.balance == Decimal("1.000000")

        history_rows = (
            await session.scalars(
                select(PaymentHistory).where(PaymentHistory.external_transaction_id == "tg_tx_1")
            )
        ).all()
        assert len(history_rows) == 1
        assert history_rows[0].provider == "telegram_stars"
        assert history_rows[0].amount == Decimal("1.000000")

        mismatched_invoice = build_stars_invoice(user_id=user.id, amount_xtr=Decimal("2"))
        with pytest.raises(StarsPaymentValidationError):
            await apply_successful_stars_payment(
                session,
                user_id=user.id,
                amount_xtr=Decimal("1"),
                telegram_transaction_id="tg_tx_2",
                telegram_charge_id="tg_charge_2",
                invoice_payload=str(mismatched_invoice["payload"]),
                provider_payment_charge_id="provider_2",
            )
        await session.commit()

    await engine.dispose()

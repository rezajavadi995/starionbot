import asyncio
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.db.base import Base
from bot.models.user import User
from bot.services.stars import apply_successful_stars_payment


def test_apply_successful_stars_payment_idempotent() -> None:
    pytest.importorskip("aiosqlite")
    asyncio.run(_scenario())


async def _scenario() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        user = User(telegram_id=99111, username="stars", full_name="Stars User", language="en")
        session.add(user)
        await session.flush()

        tx1 = await apply_successful_stars_payment(
            session,
            user_id=user.id,
            amount_xtr=Decimal("120"),
            telegram_transaction_id="tg_tx_1",
            telegram_charge_id="tg_charge_1",
            invoice_payload="payload_1",
            provider_payment_charge_id="provider_1",
        )
        tx2 = await apply_successful_stars_payment(
            session,
            user_id=user.id,
            amount_xtr=Decimal("120"),
            telegram_transaction_id="tg_tx_1",
            telegram_charge_id="tg_charge_1",
            invoice_payload="payload_1",
            provider_payment_charge_id="provider_1",
        )
        assert tx1.id == tx2.id
        await session.commit()

    await engine.dispose()

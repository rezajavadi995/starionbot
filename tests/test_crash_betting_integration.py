import asyncio
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.db.base import Base
from bot.models.transaction import TransactionType
from bot.models.user import User
from bot.models.wallet import AssetType, Wallet
from bot.services.crash_betting import finalize_round_losses, place_bet
from bot.services.ledger import apply_wallet_transaction


def test_place_bet_idempotency_and_finalize_losses() -> None:
    pytest.importorskip("aiosqlite")
    asyncio.run(_scenario())


async def _scenario() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with maker() as session:
        user = User(telegram_id=123456, username="tester", full_name="Test User", language="en")
        session.add(user)
        await session.flush()

        wallet = Wallet(user_id=user.id, asset=AssetType.STARS, balance=Decimal("100"))
        session.add(wallet)
        await session.commit()

    async with maker() as session:
        first = await place_bet(
            session,
            user_id=1,
            runtime_round_id=777,
            asset=AssetType.STARS,
            amount=Decimal("10"),
            idempotency_key="idem-key-777",
            betting_open=True,
        )
        second = await place_bet(
            session,
            user_id=1,
            runtime_round_id=777,
            asset=AssetType.STARS,
            amount=Decimal("10"),
            idempotency_key="idem-key-777",
            betting_open=True,
        )
        assert first.bet_id == second.bet_id

        closed_count = await finalize_round_losses(
            session,
            runtime_round_id=777,
            crash_multiplier=Decimal("2.21"),
            crash_point=Decimal("2.18"),
        )
        assert closed_count == 1
        await session.commit()

    async with maker() as session:
        replay = await apply_wallet_transaction(
            session,
            user_id=1,
            asset=AssetType.STARS,
            tx_type=TransactionType.BET,
            amount=Decimal("10"),
            idempotency_key="bet:idem-key-777",
        )
        assert replay.idempotency_key == "bet:idem-key-777"
        await session.commit()

    await engine.dispose()

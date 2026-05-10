import asyncio
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.db.base import Base
from bot.models.transaction import TransactionType
from bot.models.user import User
from bot.models.wallet import AssetType, Wallet
from bot.services.crash_betting import (
    CashoutUnavailableError,
    cashout_bet,
    finalize_round_losses,
    place_bet,
)
from bot.services.crash_reconciliation import persist_round_financials, reconcile_round
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

        cashed_once = await cashout_bet(
            session,
            bet_id=first.bet_id,
            current_multiplier=Decimal("1.50"),
            round_state_active=True,
            cashout_window_open=True,
            idempotency_key="cashout-key-1",
            runtime_round_id=777,
        )
        cashed_twice_same_key = await cashout_bet(
            session,
            bet_id=first.bet_id,
            current_multiplier=Decimal("1.80"),
            round_state_active=True,
            cashout_window_open=True,
            idempotency_key="cashout-key-1",
            runtime_round_id=777,
        )
        assert cashed_once.id == cashed_twice_same_key.id

        with pytest.raises(CashoutUnavailableError):
            await cashout_bet(
                session,
                bet_id=first.bet_id,
                current_multiplier=Decimal("2.00"),
                round_state_active=True,
                cashout_window_open=True,
                idempotency_key="cashout-key-2",
                runtime_round_id=999,
            )

        closed_count = await finalize_round_losses(
            session,
            runtime_round_id=777,
            crash_multiplier=Decimal("2.21"),
            crash_point=Decimal("2.18"),
        )
        assert closed_count == 0

        report = await reconcile_round(session, runtime_round_id=777)
        assert report.total_stake == Decimal("10.000000")
        assert report.cashed_out_count == 1
        assert report.house_profit == Decimal("-5.000000")
        saved = await persist_round_financials(session, report=report)
        assert saved.runtime_round_id == 777
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

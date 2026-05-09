from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.crash import CrashBet, CrashBetState, CrashRoundRecord, CrashRoundState
from bot.models.transaction import TransactionType
from bot.models.wallet import AssetType
from bot.services.ledger import apply_wallet_transaction


class BettingClosedError(ValueError):
    pass


class CashoutUnavailableError(ValueError):
    pass


@dataclass(slots=True)
class BetPlacementResult:
    bet_id: int
    round_id: int


async def place_bet(
    session: AsyncSession,
    *,
    user_id: int,
    runtime_round_id: int,
    asset: AssetType,
    amount: Decimal,
    idempotency_key: str,
    betting_open: bool,
) -> BetPlacementResult:
    existing = await session.scalar(
        select(CrashBet).where(CrashBet.bet_idempotency_key == idempotency_key)
    )
    if existing is not None:
        return BetPlacementResult(bet_id=existing.id, round_id=runtime_round_id)

    if not betting_open:
        raise BettingClosedError("betting window is closed")

    await apply_wallet_transaction(
        session,
        user_id=user_id,
        asset=asset,
        tx_type=TransactionType.BET,
        amount=amount,
        idempotency_key=f"bet:{idempotency_key}",
    )

    round_record = await session.scalar(
        select(CrashRoundRecord).where(CrashRoundRecord.runtime_round_id == runtime_round_id)
    )
    if round_record is None:
        round_record = CrashRoundRecord(
            runtime_round_id=runtime_round_id,
            state=CrashRoundState.WAITING,
            crash_point=Decimal("0"),
            crash_multiplier=Decimal("0"),
        )
        session.add(round_record)
        await session.flush()

    bet = CrashBet(
        round_id=round_record.id,
        user_id=user_id,
        asset=asset.value,
        stake_amount=amount,
        cashout_multiplier=None,
        payout_amount=None,
        bet_idempotency_key=idempotency_key,
        state=CrashBetState.PLACED,
    )
    session.add(bet)
    await session.flush()
    return BetPlacementResult(bet_id=bet.id, round_id=runtime_round_id)


async def cashout_bet(
    session: AsyncSession,
    *,
    bet_id: int,
    current_multiplier: Decimal,
    round_state_active: bool,
    idempotency_key: str,
) -> CrashBet:
    bet = await session.scalar(select(CrashBet).where(CrashBet.id == bet_id).with_for_update())
    if bet is None or bet.state != CrashBetState.PLACED or not round_state_active:
        raise CashoutUnavailableError("cashout unavailable")

    payout = (bet.stake_amount * current_multiplier).quantize(Decimal("0.000001"))
    bet.cashout_multiplier = current_multiplier
    bet.payout_amount = payout
    bet.state = CrashBetState.CASHED_OUT

    await apply_wallet_transaction(
        session,
        user_id=bet.user_id,
        asset=AssetType(bet.asset),
        tx_type=TransactionType.CASHOUT,
        amount=payout,
        idempotency_key=f"cashout:{idempotency_key}",
    )
    await session.flush()
    return bet


async def finalize_round_losses(
    session: AsyncSession,
    *,
    runtime_round_id: int,
    crash_multiplier: Decimal,
    crash_point: Decimal,
) -> int:
    round_record = await session.scalar(
        select(CrashRoundRecord)
        .where(CrashRoundRecord.runtime_round_id == runtime_round_id)
        .with_for_update()
    )
    if round_record is None:
        round_record = CrashRoundRecord(
            runtime_round_id=runtime_round_id,
            state=CrashRoundState.CRASHED,
            crash_point=crash_point,
            crash_multiplier=crash_multiplier,
        )
        session.add(round_record)
        await session.flush()
    else:
        round_record.state = CrashRoundState.CRASHED
        round_record.crash_point = crash_point
        round_record.crash_multiplier = crash_multiplier

    open_bets = (
        await session.scalars(
            select(CrashBet)
            .where(CrashBet.round_id == round_record.id, CrashBet.state == CrashBetState.PLACED)
            .with_for_update()
        )
    ).all()
    for bet in open_bets:
        bet.state = CrashBetState.LOST

    await session.flush()
    return len(open_bets)

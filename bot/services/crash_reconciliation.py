from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.crash import CrashBet, CrashBetState, CrashRoundRecord


@dataclass(slots=True)
class RoundReconciliation:
    runtime_round_id: int
    total_stake: Decimal
    total_payout: Decimal
    house_profit: Decimal
    placed_count: int
    cashed_out_count: int
    lost_count: int


async def reconcile_round(session: AsyncSession, *, runtime_round_id: int) -> RoundReconciliation:
    round_record = await session.scalar(
        select(CrashRoundRecord).where(CrashRoundRecord.runtime_round_id == runtime_round_id)
    )
    if round_record is None:
        raise ValueError("round not found")

    aggregates = await session.execute(
        select(
            func.coalesce(func.sum(CrashBet.stake_amount), 0),
            func.coalesce(func.sum(CrashBet.payout_amount), 0),
            func.count(CrashBet.id),
            func.sum(case((CrashBet.state == CrashBetState.CASHED_OUT, 1), else_=0)),
            func.sum(case((CrashBet.state == CrashBetState.LOST, 1), else_=0)),
        ).where(CrashBet.round_id == round_record.id)
    )
    total_stake, total_payout, total_count, cashed_out_count, lost_count = aggregates.one()
    total_stake_d = Decimal(str(total_stake))
    total_payout_d = Decimal(str(total_payout))
    house_profit = total_stake_d - total_payout_d
    return RoundReconciliation(
        runtime_round_id=runtime_round_id,
        total_stake=total_stake_d,
        total_payout=total_payout_d,
        house_profit=house_profit,
        placed_count=int(total_count) - int(cashed_out_count) - int(lost_count),
        cashed_out_count=int(cashed_out_count),
        lost_count=int(lost_count),
    )

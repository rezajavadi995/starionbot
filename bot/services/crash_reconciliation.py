from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.crash import CrashBet, CrashBetState, CrashRoundRecord
from bot.models.crash_financial import CrashRoundFinancial


@dataclass(slots=True)
class RoundReconciliation:
    runtime_round_id: int
    total_stake: Decimal
    total_payout: Decimal
    house_profit: Decimal
    placed_count: int
    cashed_out_count: int
    lost_count: int
    round_record_id: int


@dataclass(slots=True)
class FinancialCrosscheckItem:
    runtime_round_id: int
    recorded_profit: Decimal | None
    recomputed_profit: Decimal
    delta: Decimal
    matched: bool


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
        round_record_id=round_record.id,
    )


async def persist_round_financials(
    session: AsyncSession, *, report: RoundReconciliation
) -> CrashRoundFinancial:
    existing = await session.scalar(
        select(CrashRoundFinancial).where(
            CrashRoundFinancial.runtime_round_id == report.runtime_round_id
        )
    )
    if existing is not None:
        existing.total_stake = report.total_stake
        existing.total_payout = report.total_payout
        existing.house_profit = report.house_profit
        await session.flush()
        return existing

    entry = CrashRoundFinancial(
        runtime_round_id=report.runtime_round_id,
        round_record_id=report.round_record_id,
        total_stake=report.total_stake,
        total_payout=report.total_payout,
        house_profit=report.house_profit,
    )
    session.add(entry)
    await session.flush()
    return entry


async def crosscheck_recent_financials(
    session: AsyncSession, *, limit: int = 25
) -> list[FinancialCrosscheckItem]:
    rounds = (
        await session.scalars(
            select(CrashRoundRecord.runtime_round_id)
            .order_by(CrashRoundRecord.runtime_round_id.desc())
            .limit(limit)
        )
    ).all()

    results: list[FinancialCrosscheckItem] = []
    for runtime_round_id in rounds:
        report = await reconcile_round(session, runtime_round_id=runtime_round_id)
        stored = await session.scalar(
            select(CrashRoundFinancial).where(
                CrashRoundFinancial.runtime_round_id == runtime_round_id
            )
        )
        recorded = Decimal(str(stored.house_profit)) if stored is not None else None
        delta = report.house_profit - (recorded if recorded is not None else Decimal("0"))
        results.append(
            FinancialCrosscheckItem(
                runtime_round_id=runtime_round_id,
                recorded_profit=recorded,
                recomputed_profit=report.house_profit,
                delta=delta,
                matched=recorded is not None and delta == Decimal("0"),
            )
        )
    return results

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert

from bot.models.crash import CrashRoundRecord, CrashRoundState


async def persist_crashed_round(
    *, runtime_round_id: int, crash_point: Decimal, crash_multiplier: Decimal
) -> None:
    from bot.db.session import SessionLocal

    async with SessionLocal() as session:
        stmt = (
            insert(CrashRoundRecord)
            .values(
                runtime_round_id=runtime_round_id,
                state=CrashRoundState.CRASHED,
                crash_point=crash_point,
                crash_multiplier=crash_multiplier,
                started_at=datetime.now(UTC),
                crashed_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=[CrashRoundRecord.runtime_round_id])
        )
        await session.execute(stmt)
        await session.commit()

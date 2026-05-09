from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class CrashRoundState(StrEnum):
    WAITING = "waiting"
    ACTIVE = "active"
    CRASHED = "crashed"


class CrashRoundRecord(Base):
    __tablename__ = "crash_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    runtime_round_id: Mapped[int] = mapped_column(index=True, unique=True)
    state: Mapped[CrashRoundState] = mapped_column(
        Enum(CrashRoundState, native_enum=False), index=True
    )
    crash_point: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    crash_multiplier: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    crashed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrashBetState(StrEnum):
    PLACED = "placed"
    CASHED_OUT = "cashed_out"
    LOST = "lost"


class CrashBet(Base):
    __tablename__ = "crash_bets"

    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("crash_rounds.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    asset: Mapped[str] = mapped_column(String(16), index=True)
    stake_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    cashout_multiplier: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    payout_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    state: Mapped[CrashBetState] = mapped_column(Enum(CrashBetState, native_enum=False), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

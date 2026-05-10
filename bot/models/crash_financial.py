from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class CrashRoundFinancial(Base):
    __tablename__ = "crash_round_financials"
    __table_args__ = (
        UniqueConstraint("runtime_round_id", name="uq_crash_round_financial_runtime"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    runtime_round_id: Mapped[int] = mapped_column(index=True)
    round_record_id: Mapped[int] = mapped_column(
        ForeignKey("crash_rounds.id", ondelete="CASCADE"), index=True
    )
    total_stake: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    total_payout: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    house_profit: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

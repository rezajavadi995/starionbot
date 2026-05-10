from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class ReferralPayoutJournal(Base):
    __tablename__ = "referral_payout_journal"
    __table_args__ = (UniqueConstraint("reference_id", name="uq_referral_payout_reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    player_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    asset: Mapped[str] = mapped_column(String(16), index=True)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    house_profit: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    reference_id: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

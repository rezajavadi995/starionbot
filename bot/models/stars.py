from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class UserStarBalance(Base):
    __tablename__ = "user_star_balance"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StarTransaction(Base):
    __tablename__ = "star_transactions"
    __table_args__ = (UniqueConstraint("telegram_transaction_id", name="uq_star_tx_telegram_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount_xtr: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    telegram_transaction_id: Mapped[str] = mapped_column(String(128), index=True)
    telegram_charge_id: Mapped[str] = mapped_column(String(128), index=True)
    invoice_payload: Mapped[str] = mapped_column(String(255), index=True)
    provider_payment_charge_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

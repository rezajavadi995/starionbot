from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class TransactionType(StrEnum):
    DEPOSIT = "deposit"
    BET = "bet"
    CASHOUT = "cashout"
    WITHDRAWAL = "withdrawal"


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"), index=True)
    tx_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, native_enum=False), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

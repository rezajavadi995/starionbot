from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class AssetType(StrEnum):
    STARS = "stars"
    TON = "ton"


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("user_id", "asset", name="uq_wallet_user_asset"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    asset: Mapped[AssetType] = mapped_column(Enum(AssetType, native_enum=False), index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

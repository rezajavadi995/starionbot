from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class CrashRoundAuditLog(Base):
    __tablename__ = "crash_round_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    runtime_round_id: Mapped[int] = mapped_column(index=True)
    bet_id: Mapped[int | None] = mapped_column(
        ForeignKey("crash_bets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

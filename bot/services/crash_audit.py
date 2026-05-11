import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.crash_audit import CrashRoundAuditLog


async def write_round_audit_log(
    session: AsyncSession,
    *,
    runtime_round_id: int,
    event_type: str,
    payload: dict[str, Any],
    bet_id: int | None = None,
) -> CrashRoundAuditLog:
    entry = CrashRoundAuditLog(
        runtime_round_id=runtime_round_id,
        bet_id=bet_id,
        event_type=event_type,
        payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
    )
    session.add(entry)
    await session.flush()
    return entry

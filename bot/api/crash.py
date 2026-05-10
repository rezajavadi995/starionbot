from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.api.ws import crash_runtime
from bot.core.config import settings
from bot.db.session import get_session
from bot.models.crash_audit import CrashRoundAuditLog
from bot.models.wallet import AssetType
from bot.services.crash_betting import (
    BettingClosedError,
    CashoutUnavailableError,
    cashout_bet,
    place_bet,
)
from bot.services.crash_reconciliation import persist_round_financials, reconcile_round
from bot.services.referral import list_referral_payouts

router = APIRouter(prefix="/crash", tags=["crash"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class PlaceBetRequest(BaseModel):
    user_id: int
    asset: AssetType
    amount: Decimal = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=64)


class CashoutRequest(BaseModel):
    bet_id: int
    idempotency_key: str = Field(min_length=8, max_length=64)


def _require_admin(admin_id: int) -> None:
    if admin_id not in settings.admin_id_set:
        raise HTTPException(status_code=403, detail="admin access required")


@router.post("/bet")
async def create_bet(payload: PlaceBetRequest, session: SessionDep) -> dict[str, int]:
    try:
        result = await place_bet(
            session,
            user_id=payload.user_id,
            runtime_round_id=crash_runtime.current_round_id,
            asset=payload.asset,
            amount=payload.amount,
            idempotency_key=payload.idempotency_key,
            betting_open=crash_runtime.betting_open,
        )
        await session.commit()
        return {"bet_id": result.bet_id, "runtime_round_id": result.round_id}
    except BettingClosedError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/cashout")
async def cashout(payload: CashoutRequest, session: SessionDep) -> dict[str, str]:
    try:
        bet = await cashout_bet(
            session,
            bet_id=payload.bet_id,
            current_multiplier=crash_runtime.current_multiplier,
            round_state_active=crash_runtime.current_state.value == "active",
            cashout_window_open=crash_runtime.cashout_window_open,
            idempotency_key=payload.idempotency_key,
            runtime_round_id=crash_runtime.current_round_id,
        )
        await session.commit()
        return {
            "status": bet.state.value,
            "payout_amount": str(bet.payout_amount),
            "multiplier": str(bet.cashout_multiplier),
        }
    except CashoutUnavailableError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/round/{runtime_round_id}/audit")
async def get_round_audit(
    runtime_round_id: int, admin_id: int, session: SessionDep
) -> dict[str, object]:
    _require_admin(admin_id)
    logs = (
        await session.scalars(
            select(CrashRoundAuditLog)
            .where(CrashRoundAuditLog.runtime_round_id == runtime_round_id)
            .order_by(CrashRoundAuditLog.id.desc())
            .limit(100)
        )
    ).all()
    return {
        "round_id": runtime_round_id,
        "items": [
            {
                "id": item.id,
                "event_type": item.event_type,
                "bet_id": item.bet_id,
                "payload": item.payload_json,
                "created_at": item.created_at.isoformat(),
            }
            for item in logs
        ],
    }


@router.get("/round/{runtime_round_id}/reconcile")
async def get_round_reconcile(
    runtime_round_id: int, admin_id: int, session: SessionDep, persist: bool = True
) -> dict[str, str | int]:
    _require_admin(admin_id)
    report = await reconcile_round(session, runtime_round_id=runtime_round_id)
    if persist:
        await persist_round_financials(session, report=report)
        await session.commit()
    return {
        "runtime_round_id": report.runtime_round_id,
        "total_stake": str(report.total_stake),
        "total_payout": str(report.total_payout),
        "house_profit": str(report.house_profit),
        "placed_count": report.placed_count,
        "cashed_out_count": report.cashed_out_count,
        "lost_count": report.lost_count,
    }


@router.get("/referrals/payouts")
async def get_referral_payouts(
    admin_id: int, session: SessionDep, limit: int = 200
) -> dict[str, object]:
    _require_admin(admin_id)
    rows = await list_referral_payouts(session, limit=limit)
    return {
        "items": [
            {
                "id": row.id,
                "referrer_user_id": row.referrer_user_id,
                "player_user_id": row.player_user_id,
                "asset": row.asset,
                "commission_amount": str(row.commission_amount),
                "house_profit": str(row.house_profit),
                "reference_id": row.reference_id,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }

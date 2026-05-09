from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from bot.api.ws import crash_runtime
from bot.db.session import get_session
from bot.models.wallet import AssetType
from bot.services.crash_betting import (
    BettingClosedError,
    CashoutUnavailableError,
    cashout_bet,
    place_bet,
)

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
            idempotency_key=payload.idempotency_key,
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

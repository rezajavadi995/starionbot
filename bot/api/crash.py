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
from bot.services.crash_audit import write_round_audit_log
from bot.services.crash_betting import (
    BettingClosedError,
    CashoutUnavailableError,
    cashout_bet,
    place_bet,
)
from bot.services.crash_reconciliation import (
    crosscheck_recent_financials,
    persist_round_financials,
    reconcile_round,
)
from bot.services.referral import list_referral_payouts
from bot.services.stars import (
    apply_successful_stars_payment,
    build_stars_invoice,
    parse_stars_invoice_payload,
    parse_telegram_successful_payment,
)
from bot.services.users import get_or_create_user

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


class StarsInvoiceRequest(BaseModel):
    user_id: int
    amount_xtr: Decimal = Field(gt=0)


class StarsConfirmRequest(BaseModel):
    telegram_user_id: int
    full_name: str
    username: str | None = None
    update_json: str


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


@router.post("/stars/invoice")
async def create_stars_invoice(payload: StarsInvoiceRequest) -> dict[str, object]:
    if not settings.stars_enabled:
        raise HTTPException(status_code=400, detail="stars payments are disabled")
    invoice = build_stars_invoice(user_id=payload.user_id, amount_xtr=payload.amount_xtr)
    return invoice


@router.post("/stars/confirm")
async def confirm_stars_payment(
    payload: StarsConfirmRequest,
    webhook_secret: str,
    session: SessionDep,
) -> dict[str, str]:
    if webhook_secret != settings.webhook_secret.get_secret_value():
        raise HTTPException(status_code=403, detail="invalid webhook secret")

    user = await get_or_create_user(
        session,
        telegram_id=payload.telegram_user_id,
        full_name=payload.full_name,
        username=payload.username,
    )
    try:
        parsed = parse_telegram_successful_payment(payload.update_json)
        payload_user_id, _ = parse_stars_invoice_payload(str(parsed["invoice_payload"]))
        if payload_user_id != user.id:
            raise HTTPException(status_code=400, detail="invoice payload user mismatch")
        await apply_successful_stars_payment(
            session,
            user_id=user.id,
            amount_xtr=Decimal(parsed["amount_xtr"]),
            telegram_transaction_id=str(parsed["telegram_transaction_id"]),
            telegram_charge_id=str(parsed["telegram_charge_id"]),
            invoice_payload=str(parsed["invoice_payload"]),
            provider_payment_charge_id=(
                None
                if parsed["provider_payment_charge_id"] is None
                else str(parsed["provider_payment_charge_id"])
            ),
        )
        await write_round_audit_log(
            session,
            runtime_round_id=0,
            event_type="payment_ingested",
            payload={
                "telegram_user_id": payload.telegram_user_id,
                "invoice_payload": str(parsed["invoice_payload"]),
                "amount_xtr": str(parsed["amount_xtr"]),
                "telegram_transaction_id": str(parsed["telegram_transaction_id"]),
            },
        )
        await session.commit()
        return {"status": "ok"}
    except Exception as exc:
        await session.rollback()
        await write_round_audit_log(
            session,
            runtime_round_id=0,
            event_type="payment_rejected",
            payload={
                "telegram_user_id": payload.telegram_user_id,
                "error": str(exc)[:300],
            },
        )
        await session.commit()
        raise


@router.get("/ton/connect-config")
async def ton_connect_config() -> dict[str, str]:
    return {
        "manifest_url": "https://ton-connect.github.io/demo-dapp-with-react-ui/tonconnect-manifest.json",
        "network": "mainnet",
    }


@router.get("/admin/financial-crosscheck")
async def financial_crosscheck(
    admin_id: int, session: SessionDep, limit: int = 25
) -> dict[str, object]:
    _require_admin(admin_id)
    rows = await crosscheck_recent_financials(session, limit=limit)
    mismatched = [row for row in rows if not row.matched]
    return {
        "checked": len(rows),
        "mismatched": len(mismatched),
        "items": [
            {
                "runtime_round_id": row.runtime_round_id,
                "recorded_profit": (
                    None if row.recorded_profit is None else str(row.recorded_profit)
                ),
                "recomputed_profit": str(row.recomputed_profit),
                "delta": str(row.delta),
                "matched": row.matched,
            }
            for row in rows
        ],
    }

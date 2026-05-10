from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.transaction import TransactionType
from bot.models.user import User
from bot.models.wallet import AssetType
from bot.services.ledger import apply_wallet_transaction

REFERRAL_RATE = Decimal("0.03")


async def settle_referral_commission_hook(
    session: AsyncSession,
    *,
    player_user_id: int,
    asset: AssetType,
    house_profit: Decimal,
    reference_id: str,
) -> Decimal:
    player = await session.scalar(select(User).where(User.id == player_user_id))
    if player is None or player.referred_by_user_id is None or house_profit <= Decimal("0"):
        return Decimal("0")

    commission = (house_profit * REFERRAL_RATE).quantize(Decimal("0.000001"))
    if commission <= Decimal("0"):
        return Decimal("0")

    await apply_wallet_transaction(
        session,
        user_id=player.referred_by_user_id,
        asset=asset,
        tx_type=TransactionType.DEPOSIT,
        amount=commission,
        idempotency_key=f"referral:{reference_id}",
    )
    return commission

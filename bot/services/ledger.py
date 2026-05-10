from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.transaction import LedgerTransaction, TransactionType
from bot.models.wallet import AssetType, Wallet


class InsufficientBalanceError(ValueError):
    pass


async def apply_wallet_transaction(
    session: AsyncSession,
    *,
    user_id: int,
    asset: AssetType,
    tx_type: TransactionType,
    amount: Decimal,
    idempotency_key: str,
) -> LedgerTransaction:
    existing = await session.scalar(
        select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing

    wallet = await session.scalar(
        select(Wallet).where(Wallet.user_id == user_id, Wallet.asset == asset).with_for_update()
    )
    if wallet is None:
        wallet = Wallet(user_id=user_id, asset=asset, balance=Decimal("0"))
        session.add(wallet)
        await session.flush()

    if tx_type in {TransactionType.BET, TransactionType.WITHDRAWAL} and wallet.balance < amount:
        raise InsufficientBalanceError("insufficient balance")

    delta = amount if tx_type in {TransactionType.DEPOSIT, TransactionType.CASHOUT} else -amount
    wallet.balance = wallet.balance + delta

    created = LedgerTransaction(
        user_id=user_id,
        wallet_id=wallet.id,
        tx_type=tx_type,
        amount=amount,
        idempotency_key=idempotency_key,
    )
    session.add(created)
    try:
        await session.flush()
    except IntegrityError as err:
        await session.rollback()
        conflict = await session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key)
        )
        if conflict is None:
            raise RuntimeError("idempotent transaction lookup failed") from err
        return conflict
    return created

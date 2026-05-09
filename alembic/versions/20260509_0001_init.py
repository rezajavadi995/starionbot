"""init

Revision ID: 20260509_0001
Revises: 
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = "20260509_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("referred_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)


    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset", sa.String(length=16), nullable=False),
        sa.Column("balance", sa.Numeric(18, 6), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"], unique=False)
    op.create_index("ix_wallets_asset", "wallets", ["asset"], unique=False)
    op.create_unique_constraint("uq_wallet_user_asset", "wallets", ["user_id", "asset"])
    op.create_table(
        "ledger_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wallet_id", sa.Integer(), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tx_type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ledger_transactions_user_id", "ledger_transactions", ["user_id"], unique=False)
    op.create_index("ix_ledger_transactions_wallet_id", "ledger_transactions", ["wallet_id"], unique=False)
    op.create_index("ix_ledger_transactions_tx_type", "ledger_transactions", ["tx_type"], unique=False)
    op.create_index("ix_ledger_transactions_idempotency_key", "ledger_transactions", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_ledger_transactions_idempotency_key", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_tx_type", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_wallet_id", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_user_id", table_name="ledger_transactions")
    op.drop_table("ledger_transactions")
    op.drop_constraint("uq_wallet_user_asset", "wallets", type_="unique")
    op.drop_index("ix_wallets_asset", table_name="wallets")
    op.drop_index("ix_wallets_user_id", table_name="wallets")
    op.drop_table("wallets")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

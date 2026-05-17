"""add stars transactions and user star balance

Revision ID: 20260510_0007
Revises: 20260510_0006
Create Date: 2026-05-10
"""

import sqlalchemy as sa

from alembic import op

revision = "20260510_0007"
down_revision = "20260510_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_star_balance",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("balance", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "star_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("amount_xtr", sa.Numeric(18, 6), nullable=False),
        sa.Column("telegram_transaction_id", sa.String(length=128), nullable=False),
        sa.Column("telegram_charge_id", sa.String(length=128), nullable=False),
        sa.Column("invoice_payload", sa.String(length=255), nullable=False),
        sa.Column("provider_payment_charge_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("telegram_transaction_id", name="uq_star_tx_telegram_id"),
    )
    op.create_index("ix_star_transactions_user_id", "star_transactions", ["user_id"], unique=False)
    op.create_index(
        "ix_star_transactions_telegram_transaction_id",
        "star_transactions",
        ["telegram_transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_star_transactions_telegram_charge_id",
        "star_transactions",
        ["telegram_charge_id"],
        unique=False,
    )
    op.create_index(
        "ix_star_transactions_invoice_payload",
        "star_transactions",
        ["invoice_payload"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_star_transactions_invoice_payload", table_name="star_transactions")
    op.drop_index("ix_star_transactions_telegram_charge_id", table_name="star_transactions")
    op.drop_index("ix_star_transactions_telegram_transaction_id", table_name="star_transactions")
    op.drop_index("ix_star_transactions_user_id", table_name="star_transactions")
    op.drop_table("star_transactions")
    op.drop_table("user_star_balance")

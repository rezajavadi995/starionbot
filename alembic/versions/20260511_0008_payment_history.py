"""add payment history

Revision ID: 20260511_0008
Revises: 20260510_0007
Create Date: 2026-05-11
"""

import sqlalchemy as sa

from alembic import op

revision = "20260511_0008"
down_revision = "20260510_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("asset", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("external_transaction_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("provider", "external_transaction_id", name="uq_payment_provider_tx"),
    )
    op.create_index("ix_payment_history_user_id", "payment_history", ["user_id"], unique=False)
    op.create_index("ix_payment_history_provider", "payment_history", ["provider"], unique=False)
    op.create_index("ix_payment_history_asset", "payment_history", ["asset"], unique=False)
    op.create_index(
        "ix_payment_history_external_transaction_id",
        "payment_history",
        ["external_transaction_id"],
        unique=False,
    )
    op.create_index("ix_payment_history_status", "payment_history", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payment_history_status", table_name="payment_history")
    op.drop_index("ix_payment_history_external_transaction_id", table_name="payment_history")
    op.drop_index("ix_payment_history_asset", table_name="payment_history")
    op.drop_index("ix_payment_history_provider", table_name="payment_history")
    op.drop_index("ix_payment_history_user_id", table_name="payment_history")
    op.drop_table("payment_history")

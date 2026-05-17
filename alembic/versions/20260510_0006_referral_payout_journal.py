"""add referral payout journal

Revision ID: 20260510_0006
Revises: 20260510_0005
Create Date: 2026-05-10
"""

import sqlalchemy as sa

from alembic import op

revision = "20260510_0006"
down_revision = "20260510_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referral_payout_journal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "referrer_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset", sa.String(length=16), nullable=False),
        sa.Column("commission_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("house_profit", sa.Numeric(18, 6), nullable=False),
        sa.Column("reference_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("reference_id", name="uq_referral_payout_reference"),
    )
    op.create_index(
        "ix_referral_payout_journal_referrer_user_id",
        "referral_payout_journal",
        ["referrer_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_referral_payout_journal_player_user_id",
        "referral_payout_journal",
        ["player_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_referral_payout_journal_asset", "referral_payout_journal", ["asset"], unique=False
    )
    op.create_index(
        "ix_referral_payout_journal_reference_id",
        "referral_payout_journal",
        ["reference_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_referral_payout_journal_reference_id", table_name="referral_payout_journal")
    op.drop_index("ix_referral_payout_journal_asset", table_name="referral_payout_journal")
    op.drop_index("ix_referral_payout_journal_player_user_id", table_name="referral_payout_journal")
    op.drop_index(
        "ix_referral_payout_journal_referrer_user_id", table_name="referral_payout_journal"
    )
    op.drop_table("referral_payout_journal")

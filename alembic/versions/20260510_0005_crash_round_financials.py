"""add crash round financials

Revision ID: 20260510_0005
Revises: 20260509_0004
Create Date: 2026-05-10
"""

import sqlalchemy as sa

from alembic import op

revision = "20260510_0005"
down_revision = "20260509_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crash_round_financials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("runtime_round_id", sa.Integer(), nullable=False),
        sa.Column(
            "round_record_id",
            sa.Integer(),
            sa.ForeignKey("crash_rounds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("total_stake", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_payout", sa.Numeric(18, 6), nullable=False),
        sa.Column("house_profit", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "settled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("runtime_round_id", name="uq_crash_round_financial_runtime"),
    )
    op.create_index(
        "ix_crash_round_financials_runtime_round_id",
        "crash_round_financials",
        ["runtime_round_id"],
        unique=False,
    )
    op.create_index(
        "ix_crash_round_financials_round_record_id",
        "crash_round_financials",
        ["round_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_crash_round_financials_round_record_id", table_name="crash_round_financials")
    op.drop_index("ix_crash_round_financials_runtime_round_id", table_name="crash_round_financials")
    op.drop_table("crash_round_financials")

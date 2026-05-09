"""crash rounds and bets

Revision ID: 20260509_0002
Revises: 20260509_0001
Create Date: 2026-05-09
"""

import sqlalchemy as sa

from alembic import op

revision = "20260509_0002"
down_revision = "20260509_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crash_rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("runtime_round_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("crash_point", sa.Numeric(10, 2), nullable=False),
        sa.Column("crash_multiplier", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "crashed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_crash_rounds_runtime_round_id",
        "crash_rounds",
        ["runtime_round_id"],
        unique=True,
    )
    op.create_index("ix_crash_rounds_state", "crash_rounds", ["state"], unique=False)

    op.create_table(
        "crash_bets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "round_id",
            sa.Integer(),
            sa.ForeignKey("crash_rounds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset", sa.String(length=16), nullable=False),
        sa.Column("stake_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("cashout_multiplier", sa.Numeric(10, 2), nullable=True),
        sa.Column("payout_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_crash_bets_round_id", "crash_bets", ["round_id"], unique=False)
    op.create_index("ix_crash_bets_user_id", "crash_bets", ["user_id"], unique=False)
    op.create_index("ix_crash_bets_asset", "crash_bets", ["asset"], unique=False)
    op.create_index("ix_crash_bets_state", "crash_bets", ["state"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_crash_bets_state", table_name="crash_bets")
    op.drop_index("ix_crash_bets_asset", table_name="crash_bets")
    op.drop_index("ix_crash_bets_user_id", table_name="crash_bets")
    op.drop_index("ix_crash_bets_round_id", table_name="crash_bets")
    op.drop_table("crash_bets")
    op.drop_index("ix_crash_rounds_state", table_name="crash_rounds")
    op.drop_index("ix_crash_rounds_runtime_round_id", table_name="crash_rounds")
    op.drop_table("crash_rounds")

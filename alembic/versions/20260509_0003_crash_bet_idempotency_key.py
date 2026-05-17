"""add crash bet idempotency key

Revision ID: 20260509_0003
Revises: 20260509_0002
Create Date: 2026-05-09
"""

import sqlalchemy as sa

from alembic import op

revision = "20260509_0003"
down_revision = "20260509_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crash_bets",
        sa.Column("bet_idempotency_key", sa.String(length=128), nullable=True),
    )
    op.execute("UPDATE crash_bets SET bet_idempotency_key = 'legacy-' || id")
    op.alter_column("crash_bets", "bet_idempotency_key", nullable=False)
    op.create_index(
        "ix_crash_bets_bet_idempotency_key",
        "crash_bets",
        ["bet_idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_crash_bets_bet_idempotency_key", table_name="crash_bets")
    op.drop_column("crash_bets", "bet_idempotency_key")

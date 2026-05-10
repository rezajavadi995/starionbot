"""add cashout idempotency and crash audit logs

Revision ID: 20260509_0004
Revises: 20260509_0003
Create Date: 2026-05-09
"""

import sqlalchemy as sa

from alembic import op

revision = "20260509_0004"
down_revision = "20260509_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crash_bets",
        sa.Column("cashout_idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_crash_bets_cashout_idempotency_key",
        "crash_bets",
        ["cashout_idempotency_key"],
        unique=True,
    )

    op.create_table(
        "crash_round_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("runtime_round_id", sa.Integer(), nullable=False),
        sa.Column("bet_id", sa.Integer(), sa.ForeignKey("crash_bets.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_crash_round_audit_logs_runtime_round_id",
        "crash_round_audit_logs",
        ["runtime_round_id"],
        unique=False,
    )
    op.create_index(
        "ix_crash_round_audit_logs_bet_id",
        "crash_round_audit_logs",
        ["bet_id"],
        unique=False,
    )
    op.create_index(
        "ix_crash_round_audit_logs_event_type",
        "crash_round_audit_logs",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_crash_round_audit_logs_event_type", table_name="crash_round_audit_logs")
    op.drop_index("ix_crash_round_audit_logs_bet_id", table_name="crash_round_audit_logs")
    op.drop_index("ix_crash_round_audit_logs_runtime_round_id", table_name="crash_round_audit_logs")
    op.drop_table("crash_round_audit_logs")

    op.drop_index("ix_crash_bets_cashout_idempotency_key", table_name="crash_bets")
    op.drop_column("crash_bets", "cashout_idempotency_key")

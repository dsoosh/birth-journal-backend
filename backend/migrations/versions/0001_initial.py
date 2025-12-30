"""initial tables

Revision ID: 0001_initial
Revises:
Create Date: 2025-12-28

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("case_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("join_code_hash", sa.Text(), nullable=False),
        sa.Column(
            "join_code_last_rotated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active','closed')", name="ck_cases_status"),
    )

    op.create_table(
        "events",
        sa.Column("event_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "case_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.case_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_seq", sa.BigInteger(), sa.Identity(always=True), nullable=False, unique=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("server_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("track", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("payload_v", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint("track IN ('labor','postpartum','meta')", name="ck_events_track"),
        sa.CheckConstraint("source IN ('woman','midwife','system')", name="ck_events_source"),
    )

    op.create_index("ix_events_case_seq", "events", ["case_id", "event_seq"], unique=False)
    op.create_index("ix_events_case_server_ts", "events", ["case_id", "server_ts"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_events_case_server_ts", table_name="events")
    op.drop_index("ix_events_case_seq", table_name="events")
    op.drop_table("events")
    op.drop_table("cases")

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base


class Midwife(Base):
    __tablename__ = "midwives"

    midwife_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)

    created_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.Index("ix_midwives_email", "email"),
    )


class Case(Base):
    __tablename__ = "cases"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, default="active")
    midwife_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("midwives.midwife_id"), nullable=True)

    join_code_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    join_code_last_rotated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    created_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    closed_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    events: Mapped[list["Event"]] = relationship(back_populates="case", lazy="raise")

    __table_args__ = (
        sa.CheckConstraint("status IN ('active','closed')", name="ck_cases_status"),
    )


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False)

    event_seq: Mapped[int] = mapped_column(sa.BigInteger, sa.Identity(always=True), nullable=False, unique=True)

    type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    ts: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    server_ts: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    track: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source: Mapped[str] = mapped_column(sa.Text, nullable=False)

    payload_v: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="1")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))

    case: Mapped[Case] = relationship(back_populates="events", lazy="raise")

    __table_args__ = (
        sa.Index("ix_events_case_seq", "case_id", "event_seq"),
        sa.Index("ix_events_case_server_ts", "case_id", "server_ts"),
        sa.CheckConstraint("track IN ('labor','postpartum','meta')", name="ck_events_track"),
        sa.CheckConstraint("source IN ('woman','midwife','system')", name="ck_events_source"),
    )

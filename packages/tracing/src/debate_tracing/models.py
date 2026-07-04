"""SQLAlchemy ORM models for DebateLab."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid


class Base(DeclarativeBase):
    pass


class DebateRun(Base):
    __tablename__ = "debate_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    topic: Mapped[str] = mapped_column(String(500))
    context: Mapped[str] = mapped_column(String(5000), default="")
    user_goal: Mapped[str] = mapped_column(String(1000))
    constraints: Mapped[str] = mapped_column(String(2000), default="")
    max_rounds: Mapped[int] = mapped_column(Integer, default=3)
    preset: Mapped[str] = mapped_column(String(64), default="technical_decision")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    selected_agents: Mapped[dict] = mapped_column(JSON, default=dict)
    rounds_count: Mapped[int] = mapped_column(Integer, default=0)
    final_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    events: Mapped[list["DebateRunEvent"]] = relationship(
        back_populates="run",
        order_by="DebateRunEvent.sequence_number",
        cascade="all, delete-orphan",
    )


class DebateRunEvent(Base):
    __tablename__ = "debate_run_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("debate_runs.id", ondelete="CASCADE"),
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    run: Mapped["DebateRun"] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_run_sequence", "run_id", "sequence_number", unique=True),
    )

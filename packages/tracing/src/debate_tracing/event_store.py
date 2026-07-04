"""Immutable event store backed by PostgreSQL."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from debate_tracing.models import DebateRunEvent


class EventStoreError(Exception):
    """Base for event store errors."""


class RunNotFoundError(EventStoreError):
    """Raised when a run ID doesn't exist."""


class PostgresEventStore:
    """Append-only event store for DebateLab runs.

    Events are immutable once written. Each event gets a monotonically
    increasing sequence_number scoped to its run_id.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def append(
        self,
        run_id: uuid.UUID,
        event_type: str,
        *,
        actor: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> DebateRunEvent:
        """Append an event and return it with its assigned sequence number."""
        next_seq = await self._next_sequence(run_id)
        event = DebateRunEvent(
            run_id=run_id,
            sequence_number=next_seq,
            event_type=event_type,
            actor=actor,
            payload=payload or {},
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_events(
        self,
        run_id: uuid.UUID,
        *,
        from_sequence: int = 1,
    ) -> list[DebateRunEvent]:
        """Get events for a run, optionally from a sequence number."""
        result = await self._session.execute(
            select(DebateRunEvent)
            .where(
                DebateRunEvent.run_id == run_id,
                DebateRunEvent.sequence_number >= from_sequence,
            )
            .order_by(DebateRunEvent.sequence_number)
        )
        return list(result.scalars().all())

    async def _next_sequence(self, run_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(DebateRunEvent.sequence_number), 0)).where(
                DebateRunEvent.run_id == run_id
            )
        )
        return result.scalar_one() + 1

    async def get_run_event_count(self, run_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(DebateRunEvent.run_id == run_id)
        )
        return result.scalar_one()

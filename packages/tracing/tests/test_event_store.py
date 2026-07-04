"""Tests for the event store and models."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from debate_tracing.event_store import PostgresEventStore
from debate_tracing.models import Base, DebateRun


@pytest.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


class TestDebateRunModel:
    async def test_create_run(self, session: AsyncSession):
        run = DebateRun(
            topic="Test topic",
            user_goal="Test goal",
            context="Test context",
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

        assert run.id is not None
        assert isinstance(run.id, uuid.UUID)
        assert run.topic == "Test topic"
        assert run.status == "pending"
        assert run.rounds_count == 0


class TestEventStore:
    async def test_append_and_retrieve_events(self, session: AsyncSession):
        run = DebateRun(topic="T", user_goal="G")
        session.add(run)
        await session.flush()

        store = PostgresEventStore(session)
        e1 = await store.append(run.id, "run_created", payload={"topic": "T"})
        e2 = await store.append(run.id, "phase_transition", payload={"to": "planning"})

        assert e1.sequence_number == 1
        assert e2.sequence_number == 2

        events = await store.get_events(run.id)
        assert len(events) == 2
        assert events[0].event_type == "run_created"
        assert events[1].event_type == "phase_transition"

    async def test_events_scoped_to_run(self, session: AsyncSession):
        run_a = DebateRun(topic="A", user_goal="G")
        run_b = DebateRun(topic="B", user_goal="G")
        session.add_all([run_a, run_b])
        await session.flush()

        store = PostgresEventStore(session)
        await store.append(run_a.id, "run_created")
        await store.append(run_b.id, "run_created")

        events_a = await store.get_events(run_a.id)
        events_b = await store.get_events(run_b.id)
        assert len(events_a) == 1
        assert len(events_b) == 1
        assert events_a[0].sequence_number == 1
        assert events_b[0].sequence_number == 1

    async def test_event_count(self, session: AsyncSession):
        run = DebateRun(topic="T", user_goal="G")
        session.add(run)
        await session.flush()

        store = PostgresEventStore(session)
        assert await store.get_run_event_count(run.id) == 0

        await store.append(run.id, "run_created")
        await store.append(run.id, "phase_transition")
        assert await store.get_run_event_count(run.id) == 2

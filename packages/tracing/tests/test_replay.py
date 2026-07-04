"""Tests for the replay module."""


import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from debate_tracing.event_store import PostgresEventStore
from debate_tracing.models import Base, DebateRun
from debate_tracing.replay import reconstruct_state


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


class TestReplay:
    async def test_replay_events(self, session):
        run = DebateRun(topic="T", user_goal="G")
        session.add(run)
        await session.flush()

        store = PostgresEventStore(session)

        await store.append(run.id, "run_created", payload={"topic": "T"})
        await store.append(run.id, "phase_transition", payload={"to_phase": "planning"})
        await store.append(
            run.id, "agents_selected", payload={"agents": [{"id": "skeptic", "name": "Skeptic"}]}
        )
        await store.append(run.id, "phase_transition", payload={"to_phase": "researching"})
        await store.append(
            run.id,
            "claim_extracted",
            payload={"claim": {"id": "C-1", "text": "Test claim"}},
        )
        await store.append(run.id, "run_completed")

        state = await reconstruct_state(store, run.id)

        assert state.status == "complete"
        assert state.current_phase == "complete"
        assert "skeptic" in state.agents
        assert len(state.claims) == 1
        assert state.claims[0]["id"] == "C-1"
        assert "run_created" in state.event_types_seen
        assert "run_completed" in state.event_types_seen

    async def test_replay_empty_run(self, session):
        run = DebateRun(topic="T", user_goal="G")
        session.add(run)
        await session.flush()

        store = PostgresEventStore(session)
        state = await reconstruct_state(store, run.id)

        assert state.status == "pending"
        assert len(state.claims) == 0
        assert len(state.event_types_seen) == 0

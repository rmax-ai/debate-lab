"""Dependency injection wiring for the API."""

from collections.abc import AsyncGenerator

from debate_tracing.emitter import EventEmitter
from debate_tracing.event_store import PostgresEventStore
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Default to in-memory SQLite for development
DATABASE_URL = "sqlite+aiosqlite:///file:debatelab?mode=memory&cache=shared&uri=true"

_engine = create_async_engine(DATABASE_URL, echo=False)
_async_session = async_sessionmaker(_engine, expire_on_commit=False)

# Shared emitter for SSE subscribers
_emitter = EventEmitter()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with _async_session() as session:
        yield session


async def get_event_store(db: AsyncSession = None) -> PostgresEventStore:
    """Get an event store for the current session."""
    if db is None:
        async with _async_session() as session:
            return PostgresEventStore(session)
    return PostgresEventStore(db)


def get_emitter() -> EventEmitter:
    """Get the shared event emitter."""
    return _emitter

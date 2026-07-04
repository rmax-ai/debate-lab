"""Dependency injection wiring for the API."""

from collections.abc import AsyncGenerator

from debate_harnesses.providers import ModelProvider
from debate_orchestrator.config import load_config
from debate_orchestrator.engine import Orchestrator
from debate_tracing.emitter import EventEmitter
from debate_tracing.event_store import PostgresEventStore
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Default to in-memory SQLite for development
DATABASE_URL = "sqlite+aiosqlite:///file:debatelab?mode=memory&cache=shared&uri=true"

_engine = create_async_engine(DATABASE_URL, echo=False)
_async_session = async_sessionmaker(_engine, expire_on_commit=False)

# Shared emitter for SSE subscribers
_emitter = EventEmitter()

# Lazy-loaded provider from config
_provider: ModelProvider | None = None


def get_provider() -> ModelProvider:
    """Get the configured model provider (lazy, cached).

    Loads debate.toml on first call; returns cached provider afterwards.
    Falls back to MockModelProvider if config is missing or keys are unavailable.
    """
    global _provider
    if _provider is None:
        config = load_config()
        _provider = config.provider
    return _provider


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


def get_orchestrator(db: AsyncSession) -> Orchestrator:
    """Build a fully-wired Orchestrator with configured provider."""
    event_store = PostgresEventStore(db)
    return Orchestrator(event_store, _emitter, provider=get_provider())

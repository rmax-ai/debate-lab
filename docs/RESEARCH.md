# RESEARCH.md — Best Practices for the DebateLab Stack

> **Purpose:** Concrete code patterns and conventions for the FastAPI + Next.js monorepo.
> **Audience:** AI coding agents (Codex, Droid) and human contributors.
> **Stack:** Python 3.12+ FastAPI | Next.js 14+ React/TS | PostgreSQL | Docker Compose

---

## Table of Contents

1. [Monorepo Structure & Tooling](#1-monorepo-structure--tooling)
2. [Python 3.12+ / FastAPI Backend](#2-python-312--fastapi-backend)
3. [TypeScript / Next.js Frontend](#3-typescript--nextjs-frontend)
4. [Domain-Specific Patterns](#4-domain-specific-patterns)
5. [Production Readiness](#5-production-readiness)

---

## 1. Monorepo Structure & Tooling

### 1.1 Directory Layout

```
debate-lab/
├── apps/
│   ├── web/              # Next.js (TypeScript)
│   │   ├── app/          # App Router pages
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   ├── stores/       # Zustand stores
│   │   ├── lib/          # Utilities, API client
│   │   ├── next.config.ts
│   │   └── package.json
│   └── api/              # FastAPI (Python)
│       ├── src/
│       │   ├── debate_lab/
│       │   │   ├── app.py          # create_app() factory
│       │   │   ├── main.py         # uvicorn entry point
│       │   │   ├── config.py       # pydantic-settings
│       │   │   ├── db.py           # async engine + sessionmaker
│       │   │   ├── models/         # SQLAlchemy ORM models
│       │   │   ├── schemas/        # Pydantic v2 schemas
│       │   │   ├── routers/        # FastAPI routers
│       │   │   ├── services/       # Business logic
│       │   │   └── dependencies.py # FastAPI Depends helpers
│       │   └── tests/
│       ├── pyproject.toml
│       └── Dockerfile
├── packages/
│   ├── orchestrator/     # Debate lifecycle + phase transitions
│   ├── harnesses/        # Agent definitions, role prompts, schemas
│   ├── tools/            # Tool gateway + search implementations
│   ├── tracing/          # Event model, persistence, replay
│   ├── evidence/         # Evidence extraction, source scoring
│   └── evals/            # Report quality checks, evidence audit
├── docs/
├── docker-compose.yml
├── pyproject.toml         # Root workspace config (uv)
├── package.json           # Root workspace config (npm/pnpm)
└── README.md
```

### 1.2 uv Workspace Configuration

**Root `pyproject.toml`:**

```toml
[project]
name = "debate-lab"
version = "0.1.0"
requires-python = ">=3.12"

[tool.uv.workspace]
members = [
    "apps/api",
    "packages/*",
]

[tool.uv.sources]
orchestrator = { workspace = true }
harnesses = { workspace = true }
tools = { workspace = true }
tracing = { workspace = true }
evidence = { workspace = true }
evals = { workspace = true }
```

**Per-package `pyproject.toml` (e.g., `apps/api/pyproject.toml`):**

```toml
[project]
name = "debate-lab-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.115.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "sse-starlette>=2.2.0",
    "structlog>=24.4.0",
    "orchestrator",
    "tracing",
    "tools",
]

[tool.uv.sources]
orchestrator = { workspace = true }
tracing = { workspace = true }
tools = { workspace = true }

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
    "ty>=0.1.0",
    "pytest-mock>=3.14",
    "faker>=33.0",
]
```

### 1.3 TypeScript Workspace (Root `package.json`)

```json
{
  "name": "debate-lab",
  "private": true,
  "workspaces": ["apps/web", "packages/*"],
  "scripts": {
    "dev": "turbo dev",
    "build": "turbo build",
    "lint": "turbo lint",
    "test": "turbo test"
  },
  "devDependencies": {
    "turbo": "^2.3.0",
    "typescript": "^5.6.0"
  }
}
```

### 1.4 GitHub Actions CI

```yaml
name: CI
on: [push, pull_request]

jobs:
  lint-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
      - run: uv sync --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run ty .

  lint-ts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm run lint
      - run: npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: debate
          POSTGRES_DB: debate_test
          POSTGRES_PASSWORD: debate
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
      - run: uv sync --group dev --group test
      - run: uv run pytest apps/api/tests/ packages/*/tests/
      - run: |
          cd apps/web && npm ci && npm test
```

---

## 2. Python 3.12+ / FastAPI Backend

### 2.1 App Factory Pattern

**`apps/api/src/debate_lab/app.py`:**

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from debate_lab.config import Settings
from debate_lab.db import create_engine, create_sessionmaker
from debate_lab.routers import debate, events, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: create engine on startup, dispose on shutdown."""
    settings: Settings = app.state.settings
    engine = create_engine(settings.database_url)
    sessionmaker = create_sessionmaker(engine)
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Factory: fast and side-effect-free. Tests call this directly."""
    if settings is None:
        settings = Settings()  # reads from .env / env vars

    app = FastAPI(
        title="DebateLab API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(debate.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")

    return app
```

**`apps/api/src/debate_lab/main.py`:**

```python
"""Entry point for `fastapi dev` / uvicorn.

Tests import `create_app` from `debate_lab.app`, NOT this module.
"""
from debate_lab.app import create_app

app = create_app()
```

### 2.2 Pydantic v2 Strict Schemas

**`apps/api/src/debate_lab/schemas/claim.py`:**

```python
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClaimStatus(str, Enum):
    PROPOSED = "proposed"
    CHALLENGED = "challenged"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    ACCEPTED = "accepted"
    UNRESOLVED = "unresolved"


class ClaimCreate(BaseModel):
    """Input schema: strict, no extra fields, field-level validators."""
    model_config = ConfigDict(
        extra="forbid",          # reject unknown fields
        strict=True,             # no type coercion
        frozen=True,             # immutable after creation
    )

    text: str = Field(..., min_length=1, max_length=2000)
    agent_id: str = Field(..., pattern=r"^agent-[a-z0-9-]+$")
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def text_must_end_with_period(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped.endswith((".", "?", "!")):
            raise ValueError("Claim text must end with sentence-ending punctuation")
        return stripped


class ClaimResponse(BaseModel):
    """Output schema: read-only, uses UUIDs, includes computed fields."""
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,    # allow construction from ORM objects
    )

    id: UUID
    text: str
    agent_id: str
    status: ClaimStatus = ClaimStatus.PROPOSED
    confidence: float | None = None
    evidence_refs: list[str] = []
    challenged_by: list[str] = []
    created_at: datetime
    updated_at: datetime


class ClaimGraphNode(BaseModel):
    """Claim graph node: structured for UI consumption."""
    model_config = ConfigDict(frozen=True)

    id: str  # e.g., "C-17"
    text: str
    agent_id: str
    status: ClaimStatus
    evidence_refs: list[str]
    children: list[ClaimGraphNode] = []


class EventPayload(BaseModel):
    """Event sourcing payload: typed per event_type, fallback to dict."""
    model_config = ConfigDict(extra="allow")  # allow extra fields for flexibility

    event_type: str
    actor: str | None = None
    data: dict = Field(default_factory=dict)
```

### 2.3 SQLAlchemy 2.0 Async

**`apps/api/src/debate_lab/db.py`:**

```python
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Naming convention for Alembic-generated constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


def create_engine(database_url: str) -> AsyncEngine:
    """Single async engine per service instance."""
    return create_async_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_pre_ping=True,
        echo=False,
    )


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Single sessionmaker per engine."""
    return async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_session(app_state) -> AsyncSession:  # type: ignore[no-untyped-def]
    """FastAPI dependency: yields a session, closes on response end."""
    sessionmaker: async_sessionmaker[AsyncSession] = app_state.sessionmaker
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**`apps/api/src/debate_lab/models/event.py`:**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = Base.metadata  # type: ignore[attr-defined]


class Event(Base):
    """Event sourcing: append-only log of all debate actions."""
    __tablename__ = "debate_run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence_number", name="uq_event_run_seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debate_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationship
    run = relationship("DebateRun", back_populates="events")
```

**Usage in a service:**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from debate_lab.models.event import Event


async def get_events_for_run(
    session: AsyncSession,
    run_id: uuid.UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Event]:
    """Fetch ordered events for a debate run."""
    stmt = (
        select(Event)
        .where(Event.run_id == run_id)
        .order_by(Event.sequence_number)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def append_event(
    session: AsyncSession,
    run_id: uuid.UUID,
    event_type: str,
    payload: dict,
    actor: str | None = None,
    next_sequence: int = 1,
) -> Event:
    """Append an immutable event to the log."""
    event = Event(
        run_id=run_id,
        sequence_number=next_sequence,
        event_type=event_type,
        actor=actor,
        payload=payload,
    )
    session.add(event)
    await session.flush()  # gets the ID without committing
    return event
```

### 2.4 SSE Streaming Endpoint

**`apps/api/src/debate_lab/routers/events.py`:**

```python
import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from debate_lab.dependencies import get_session
from debate_lab.services.event_stream import event_emitter

router = APIRouter(tags=["events"])


@router.get("/debates/{run_id}/stream")
async def stream_debate_events(
    run_id: uuid.UUID,
    request: Request,
    session=Depends(get_session),
) -> EventSourceResponse:
    """SSE endpoint: streams debate events as they happen.

    - Uses sse-starlette for typed ServerSentEvent objects
    - Built-in ping keepalive every 15s to prevent proxy timeouts
    - Automatic client disconnect detection
    """

    async def event_generator():
        event_id = 0
        async for event_payload in event_emitter(session, run_id):
            if await request.is_disconnected():
                break
            event_id += 1
            yield ServerSentEvent(
                data=json.dumps(event_payload, default=str),
                event=event_payload.get("event_type", "update"),
                id=str(event_id),
            )
            await asyncio.sleep(0)  # yield control to event loop

    return EventSourceResponse(
        event_generator(),
        ping=15,  # send SSE comment every 15s to keep connection alive
        ping_message_factory=lambda: ServerSentEvent(comment="ping"),
    )
```

**`apps/api/src/debate_lab/services/event_stream.py`:**

```python
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from debate_lab.models.event import Event


async def event_emitter(
    session: AsyncSession,
    run_id: uuid.UUID,
    poll_interval: float = 0.25,
) -> AsyncIterator[dict]:
    """Poll for new events and yield them as they arrive.

    For MVP: simple polling every 250ms.
    For production: replace with Postgres LISTEN/NOTIFY or a message queue.
    """
    last_seen_id = -1
    while True:
        stmt = (
            select(Event)
            .where(
                Event.run_id == run_id,
                Event.sequence_number > last_seen_id,
            )
            .order_by(Event.sequence_number)
        )
        result = await session.execute(stmt)
        events = list(result.scalars().all())

        for event in events:
            payload = {
                "id": str(event.id),
                "run_id": str(event.run_id),
                "sequence_number": event.sequence_number,
                "event_type": event.event_type,
                "actor": event.actor,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }
            yield payload
            last_seen_id = event.sequence_number

        await asyncio.sleep(poll_interval)
```

### 2.5 Dependency Injection

**`apps/api/src/debate_lab/dependencies.py`:**

```python
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: provides an async DB session per request."""
    sessionmaker: async_sessionmaker[AsyncSession] = (
        request.app.state.sessionmaker
    )
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_settings(request: Request):
    return request.app.state.settings
```

### 2.6 Structured Logging with structlog

**`apps/api/src/debate_lab/logging_config.py`:**

```python
import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer


def configure_logging(*, json_output: bool = False) -> None:
    """Configure structlog with shared processors.

    - Development: rich console output
    - Production: JSON output for log aggregators
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.set_exc_info,
    ]

    if json_output:
        # Production: JSON
        processors = shared_processors + [JSONRenderer()]
    else:
        # Development: colored console
        processors = shared_processors + [
            ConsoleRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Module-level logger factory
logger: structlog.stdlib.BoundLogger = structlog.get_logger()
```

**Usage in FastAPI middleware:**

```python
from fastapi import Request, Response
from debate_lab.logging_config import logger


async def logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "unknown")
    structlog.contextvars.bind_contextvars(request_id=request_id)

    logger.info("request_started", method=request.method, path=request.url.path)

    response: Response = await call_next(request)

    logger.info(
        "request_completed",
        status_code=response.status_code,
        duration_ms=...,
    )
    return response
```

### 2.7 Testing (pytest-asyncio + Mock Providers)

**`apps/api/tests/conftest.py`:**

```python
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from debate_lab.app import create_app
from debate_lab.db import Base, get_session


@pytest.fixture(scope="session")
def anyio_backend():
    """Required by pytest-asyncio for session-scoped fixtures."""
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite for fast tests. Use testcontainers for integration."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Fresh session per test, rolled back on completion."""
    factory = async_sessionmaker(
        db_engine, expire_on_commit=False, class_=AsyncSession,
    )
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with DB dependency overridden."""
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

**Test example:**

```python
import pytest
from unittest.mock import AsyncMock

from debate_lab.services.event_stream import event_emitter


@pytest.mark.asyncio
async def test_append_and_read_events(db_session):
    """Verify event appending and ordered retrieval."""
    from debate_lab.models.event import Event

    # Arrange
    run_id = uuid.uuid4()
    event1 = Event(
        run_id=run_id, sequence_number=1,
        event_type="run_created", payload={"topic": "AI Safety"},
    )
    event2 = Event(
        run_id=run_id, sequence_number=2,
        event_type="agent_selected", payload={"agent": "skeptic"},
    )
    db_session.add_all([event1, event2])
    await db_session.flush()

    # Act
    stmt = select(Event).where(Event.run_id == run_id).order_by(Event.sequence_number)
    result = await db_session.execute(stmt)
    events = list(result.scalars().all())

    # Assert
    assert len(events) == 2
    assert events[0].event_type == "run_created"
    assert events[1].event_type == "agent_selected"
```

**Mock provider example:**

```python
from typing import Protocol, Any
from pydantic import BaseModel


class ModelProvider(Protocol):
    """Protocol for LLM provider adapters."""

    async def generate(
        self,
        prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel: ...


class MockProvider:
    """Deterministic mock: returns a fully-specified response for tests.

    The `responses` dict maps prompt-hash → dict literal that validates
    against the target schema.
    """

    def __init__(self, responses: dict[str, dict[str, Any]] | None = None) -> None:
        self.responses = responses or {}

    async def generate(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        """Return pre-configured response matching the schema."""
        key = str(hash(prompt))
        if key in self.responses:
            return schema.model_validate(self.responses[key])
        # Fallback: return a schema with default/dummy values
        return schema.model_validate(schema.model_construct().__dict__)
```

### 2.8 Ruff + ty Configuration

**In root `pyproject.toml`:**

```toml
[tool.ruff]
target-version = "py312"
line-length = 88
exclude = [".venv", "node_modules", ".git", "dist", "build", "**/migrations/"]

[tool.ruff.lint]
select = [
    "E4", "E7", "E9", "F",      # pyflakes + pycodestyle
    "I",                         # isort
    "N",                         # pep8-naming
    "UP",                        # pyupgrade
    "B",                         # flake8-bugbear
    "SIM",                       # flake8-simplify
    "ARG",                       # flake8-unused-arguments
    "RUF100",                    # unused noqa directives
]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.format]
quote-style = "double"
docstring-code-format = true

[tool.ty]
python-version = "3.12"

[tool.ty.rules]
possibly-unresolved-reference = "warn"
division-by-zero = "error"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["apps/api/tests", "packages/*/tests"]
```

---

## 3. TypeScript / Next.js Frontend

### 3.1 Next.js App Router Patterns

**Server Component (default, no `'use client'`):**

```tsx
// apps/web/app/debates/[runId]/page.tsx
import { notFound } from "next/navigation";
import { DebateTimeline } from "@/components/debate-timeline";
import { api } from "@/lib/api";

interface PageProps {
  params: Promise<{ runId: string }>;
}

export async function generateMetadata({ params }: PageProps) {
  const { runId } = await params;
  const run = await api.getDebateRun(runId);
  return { title: `Debate: ${run.topic}` };
}

export default async function DebatePage({ params }: PageProps) {
  const { runId } = await params;
  const run = await api.getDebateRun(runId);

  if (!run) notFound();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{run.topic}</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {/* async server component — no loading boilerplate */}
          <DebateTimeline runId={runId} initialRun={run} />
        </div>
        <aside>
          {/* client island for interactive agent panel */}
          <AgentPanel runId={runId} />
        </aside>
      </div>
    </div>
  );
}
```

**Client Component (interactive island):**

```tsx
"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDebateStream } from "@/hooks/use-debate-stream";
import { useAgentStore } from "@/stores/agent-store";

interface AgentPanelProps {
  runId: string;
}

export function AgentPanel({ runId }: AgentPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { activeAgent, events } = useDebateStream(runId);
  const { agents } = useAgentStore();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${activeAgent ? "bg-green-500" : "bg-gray-300"}`} />
          {activeAgent ?? "No active agent"}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <pre className="text-xs overflow-auto max-h-96">
          {JSON.stringify(events.slice(-10), null, 2)}
        </pre>
      </CardContent>
    </Card>
  );
}
```

### 3.2 Zustand Store (Client State)

```tsx
// apps/web/stores/agent-store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";

interface Agent {
  id: string;
  name: string;
  role: string;
  status: "idle" | "working" | "completed" | "error";
}

interface AgentState {
  agents: Agent[];
  activeAgentId: string | null;
  setAgents: (agents: Agent[]) => void;
  setActiveAgent: (id: string | null) => void;
  updateAgentStatus: (id: string, status: Agent["status"]) => void;
}

export const useAgentStore = create<AgentState>()(
  devtools(
    (set) => ({
      agents: [],
      activeAgentId: null,

      setAgents: (agents) => set({ agents }),

      setActiveAgent: (id) => set({ activeAgentId: id }),

      updateAgentStatus: (id, status) =>
        set((state) => ({
          agents: state.agents.map((a) =>
            a.id === id ? { ...a, status } : a,
          ),
        })),
    }),
    { name: "agent-store" },
  ),
);
```

### 3.3 TanStack Query (Server State)

```tsx
// apps/web/hooks/use-debate-run.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useDebateRun(runId: string) {
  return useQuery({
    queryKey: ["debate-run", runId],
    queryFn: () => api.getDebateRun(runId),
    staleTime: 30_000,       // 30s before considered stale
    gcTime: 5 * 60_000,      // keep in cache 5 min after unmount
    refetchOnWindowFocus: true,
  });
}

export function useClaimGraph(runId: string) {
  return useQuery({
    queryKey: ["claim-graph", runId],
    queryFn: () => api.getClaimGraph(runId),
    staleTime: 10_000,
  });
}

export function useCreateDebate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { topic: string; context: string }) =>
      api.createDebateRun(input),
    onSuccess: (newRun) => {
      queryClient.setQueryData(["debate-run", newRun.id], newRun);
      queryClient.invalidateQueries({ queryKey: ["debate-runs"] });
    },
  });
}
```

### 3.4 SSE EventSource Hook

```tsx
// apps/web/hooks/use-debate-stream.ts
"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAgentStore } from "@/stores/agent-store";

interface DebateEvent {
  id: string;
  run_id: string;
  sequence_number: number;
  event_type: string;
  actor: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

interface UseDebateStreamResult {
  events: DebateEvent[];
  isConnected: boolean;
  activeAgent: string | null;
  lastEvent: DebateEvent | null;
  error: string | null;
}

export function useDebateStream(runId: string): UseDebateStreamResult {
  const [events, setEvents] = useState<DebateEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const { updateAgentStatus } = useAgentStore();

  const connect = useCallback(() => {
    const es = new EventSource(`/api/v1/debates/${runId}/stream`);

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    es.addEventListener("update", (event) => {
      const data: DebateEvent = JSON.parse(event.data);
      setEvents((prev) => {
        // deduplicate by sequence_number (SSE may redeliver on reconnect)
        if (prev.some((e) => e.sequence_number === data.sequence_number)) {
          return prev;
        }
        return [...prev, data];
      });
    });

    es.onerror = () => {
      setIsConnected(false);
      setError("Connection lost. Retrying...");
      es.close();

      // Exponential backoff reconnect
      const delay = Math.min(1000 * 2 ** (reconnectTimeoutRef.current ? 1 : 0), 30_000);
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    eventSourceRef.current = es;
  }, [runId]);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
      clearTimeout(reconnectTimeoutRef.current);
    };
  }, [connect]);

  const lastEvent = events.length > 0 ? events[events.length - 1] : null;
  const activeAgent = lastEvent?.actor ?? null;

  return { events, isConnected, activeAgent, lastEvent, error };
}
```

### 3.5 Vitalest + React Testing Library

```tsx
// apps/web/__tests__/agent-panel.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentPanel } from "@/components/agent-panel";
import { useDebateStream } from "@/hooks/use-debate-stream";

// Mock the SSE hook
vi.mock("@/hooks/use-debate-stream", () => ({
  useDebateStream: vi.fn(),
}));

describe("AgentPanel", () => {
  beforeEach(() => {
    vi.mocked(useDebateStream).mockReturnValue({
      events: [],
      isConnected: true,
      activeAgent: "skeptic-01",
      lastEvent: null,
      error: null,
    });
  });

  it("renders the active agent name", () => {
    render(<AgentPanel runId="test-run" />);
    expect(screen.getByText("skeptic-01")).toBeDefined();
  });

  it("shows connected status indicator", () => {
    render(<AgentPanel runId="test-run" />);
    const indicator = screen.getByRole("generic");
    expect(indicator.className).toContain("bg-green-500");
  });

  it("displays recent events", () => {
    vi.mocked(useDebateStream).mockReturnValue({
      events: [
        { id: "1", run_id: "r1", sequence_number: 1, event_type: "run_created", actor: null, payload: {}, created_at: "2025-01-01T00:00:00Z" },
      ],
      isConnected: true,
      activeAgent: null,
      lastEvent: null,
      error: null,
    });
    render(<AgentPanel runId="test-run" />);
    expect(screen.getByText(/run_created/)).toBeDefined();
  });
});
```

### 3.6 shadcn/ui Usage Pattern

```tsx
// components/ui/card.tsx — generated by `npx shadcn@latest add card`
import * as React from "react";
import { cn } from "@/lib/utils";

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("rounded-xl border bg-card text-card-foreground shadow-sm", className)}
      {...props}
    />
  ),
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("font-semibold leading-none tracking-tight", className)} {...props} />
  ),
);
CardTitle.displayName = "CardTitle";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

export { Card, CardHeader, CardTitle, CardContent };
```

---

## 4. Domain-Specific Patterns

### 4.1 Event Sourcing with PostgreSQL JSONB

**Immutable event log pattern:**

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    """Immutable domain event.

    Rules:
    - Created once, never mutated.
    - Named after business facts, not DB operations (e.g. 'ClaimChallenged', not 'UpdateClaim').
    - Payload is a dict for JSONB storage.
    - Metadata (correlation_id, causation_id) is separate from domain data.
    """
    aggregate_id: str
    event_type: str
    payload: dict[str, Any]
    metadata: dict[str, Any] | None = None
    sequence: int = 1
    occurred_at: datetime = datetime.now(timezone.utc)


class PostgresEventStore:
    """Append-only event store backed by PostgreSQL JSONB.

    Concurrency: UNIQUE(aggregate_id, sequence) constraint provides
    optimistic concurrency — INSERT fails if the sequence already exists.
    """

    def __init__(self, session) -> None: ...

    async def append(self, event: DomainEvent) -> None:
        """Append an event. Raises on sequence conflict."""
        from debate_lab.models.event import Event

        db_event = Event(
            run_id=uuid.UUID(event.aggregate_id) if len(event.aggregate_id) == 36 else None,
            sequence_number=event.sequence,
            event_type=event.event_type,
            actor=event.metadata.get("actor") if event.metadata else None,
            payload={**event.payload, **(event.metadata or {})},
        )
        self._session.add(db_event)
        await self._session.flush()  # unique constraint violation raises here

    async def get_stream(
        self,
        aggregate_id: str,
        from_sequence: int = 0,
    ) -> list[DomainEvent]:
        """Replay events for an aggregate in order."""
        query = (
            select(Event)
            .where(
                Event.run_id == uuid.UUID(aggregate_id),
                Event.sequence_number > from_sequence,
            )
            .order_by(Event.sequence_number)
        )
        result = await self._session.execute(query)
        return [
            DomainEvent(
                aggregate_id=str(e.run_id),
                event_type=e.event_type,
                payload=e.payload,
                sequence=e.sequence_number,
            )
            for e in result.scalars().all()
        ]


def reconstitute_from_events(events: list[DomainEvent]) -> dict[str, Any]:
    """Left-fold over events to rebuild aggregate state.

    Pure function — no side effects, deterministic.
    """
    state: dict[str, Any] = {
        "status": "pending",
        "agents": [],
        "claims": [],
        "current_phase": None,
    }

    for event in events:
        if event.event_type == "run_created":
            state["status"] = "running"
            state["topic"] = event.payload.get("topic")
        elif event.event_type == "agents_selected":
            state["agents"] = event.payload.get("agents", [])
        elif event.event_type == "claim_extracted":
            state["claims"].append(event.payload)
        elif event.event_type == "phase_transition":
            state["current_phase"] = event.payload.get("to_phase")
        elif event.event_type == "run_completed":
            state["status"] = "complete"
        elif event.event_type == "run_failed":
            state["status"] = "failed"

    return state
```

### 4.2 Mock Provider Pattern

```python
from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class ModelProvider(Protocol):
    """Protocol for LLM provider adapters.

    All providers must accept a Pydantic schema and return a validated instance.
    No raw text responses allowed anywhere.
    """

    async def generate(
        self,
        prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel: ...


class MockProvider:
    """Deterministic mock for testing.

    Uses a registry of pre-built responses keyed by schema type name.
    Falls back to schema defaults + faker for unregistered schemas.
    """

    def __init__(self, fixtures: dict[str, dict[str, Any]] | None = None) -> None:
        self._fixtures = fixtures or {}
        self.call_count = 0
        self.last_prompt: str | None = None

    async def generate(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        self.call_count += 1
        self.last_prompt = prompt

        schema_name = schema.__name__
        if schema_name in self._fixtures:
            return schema.model_validate(self._fixtures[schema_name])

        # Fallback: construct with all-default fields
        return schema.model_validate(schema.model_construct().__dict__)

    def add_fixture(self, schema_name: str, data: dict[str, Any]) -> None:
        self._fixtures[schema_name] = data


# Deterministic fixtures for the Advocate harness
ADVOCATE_FIXTURES: dict[str, dict[str, Any]] = {
    "OpeningPosition": {
        "position": "PostgreSQL is the optimal choice for most web applications.",
        "claims": ["C-1", "C-2"],
        "confidence": 0.85,
        "evidence_refs": ["evt-website-001"],
    },
    "Challenge": {
        "target_claim_id": "C-1",
        "objection": "The claim ignores scaling costs at very large data volumes.",
        "counter_evidence_refs": ["evt-website-002"],
    },
}
```

### 4.3 Structured Debate Protocol

```python
from __future__ import annotations

from enum import Enum, auto
from typing import Any


class Phase(str, Enum):
    """Deterministic phase transitions enforced by the orchestrator.

    These map to the visual status model shown in the UI.
    """
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    ARGUING = "arguing"
    CHALLENGING = "challenging"
    REVISING = "revising"
    SYNTHESIZING = "synthesizing"
    AUDITING = "auditing"
    COMPLETE = "complete"
    FAILED = "failed"


# Valid transitions: from_phase -> [to_phase, ...]
PHASE_TRANSITIONS: dict[Phase, list[Phase]] = {
    Phase.PENDING: [Phase.PLANNING, Phase.FAILED],
    Phase.PLANNING: [Phase.RESEARCHING, Phase.FAILED],
    Phase.RESEARCHING: [Phase.ARGUING, Phase.FAILED],
    Phase.ARGUING: [Phase.CHALLENGING, Phase.FAILED],
    Phase.CHALLENGING: [Phase.REVISING, Phase.FAILED],
    Phase.REVISING: [Phase.ARGUING, Phase.SYNTHESIZING, Phase.FAILED],  # loop back for more rounds or advance
    Phase.SYNTHESIZING: [Phase.AUDITING, Phase.FAILED],
    Phase.AUDITING: [Phase.COMPLETE, Phase.FAILED],
    Phase.COMPLETE: [],
    Phase.FAILED: [],
}


class PhaseEngine:
    """State machine that enforces deterministic phase transitions."""

    def __init__(self, max_revision_rounds: int = 3) -> None:
        self._current = Phase.PENDING
        self._revision_count = 0
        self._max_revision_rounds = max_revision_rounds

    @property
    def current(self) -> Phase:
        return self._current

    def transition(self, to_phase: Phase) -> None:
        """Transition to a new phase. Raises ValueError if invalid."""
        allowed = PHASE_TRANSITIONS.get(self._current, [])
        if to_phase not in allowed:
            raise ValueError(
                f"Cannot transition from {self._current.value} to {to_phase.value}. "
                f"Allowed: {[p.value for p in allowed]}"
            )

        # Auto-limit revision rounds
        if to_phase == Phase.REVISING:
            self._revision_count += 1
            if self._revision_count > self._max_revision_rounds:
                # Skip to synthesis
                self._current = Phase.SYNTHESIZING
                return

        self._current = to_phase

    def can_advance(self) -> bool:
        """Convergence check: have positions stabilized?"""
        return (
            self._current in {Phase.REVISING, Phase.ARGUING}
            and self._revision_count >= self._max_revision_rounds
        )
```

### 4.4 Tool Gateway Pattern

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, Field


class Tool(Protocol):
    """Tool interface: every tool is a callable class."""

    name: str
    description: str

    async def execute(self, params: dict[str, Any]) -> ToolResult: ...


@dataclass
class ToolResult:
    """Structured result from any tool execution."""
    success: bool
    data: dict[str, Any]
    raw_output: str | None = None
    error: str | None = None
    evidence_refs: list[EvidenceRef] = field(default_factory=list)


@dataclass
class EvidenceRef:
    """A single piece of evidence extracted from a tool result."""
    source_url: str
    title: str
    excerpt: str
    facts: list[str]
    reliability_score: float = 0.5


class PolicyConfig(BaseModel):
    """Per-harness tool policy."""
    model_config = {"extra": "forbid"}

    agent_id: str
    allowed_tools: list[str] = Field(default_factory=list)
    max_tool_calls_per_run: int = 20
    max_tool_calls_per_agent: int = 10
    read_only: bool = True


class ToolGateway:
    """Mediated tool execution with policy enforcement and evidence extraction.

    Flow:
    Agent -> ToolGateway.execute() -> PolicyCheck -> Tool.exec() -> EvidenceExtractor -> return
    """

    def __init__(self, tools: dict[str, Tool], policies: dict[str, PolicyConfig]) -> None:
        self._tools = tools
        self._policies = policies
        self._call_counts: dict[str, int] = {}  # agent_id -> call count

    async def execute(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
        run_id: uuid.UUID | None = None,
    ) -> ToolResult:
        # 1. Policy check
        policy = self._policies.get(agent_id)
        if not policy:
            return ToolResult(success=False, data={}, error=f"No policy for agent '{agent_id}'")

        if tool_name not in policy.allowed_tools:
            return ToolResult(
                success=False,
                data={},
                error=f"Tool '{tool_name}' not in allowlist for agent '{agent_id}'",
            )

        self._call_counts[agent_id] = self._call_counts.get(agent_id, 0) + 1
        if self._call_counts[agent_id] > policy.max_tool_calls_per_agent:
            return ToolResult(
                success=False,
                data={},
                error=f"Agent '{agent_id}' exceeded max tool calls ({policy.max_tool_calls_per_agent})",
            )

        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, data={}, error=f"Unknown tool '{tool_name}'")

        # 2. Execute
        result = await tool.execute(params)

        # 3. Extract evidence (if successful)
        if result.success:
            evidence = await self._extract_evidence(tool_name, result)
            result.evidence_refs = evidence

        return result

    async def _extract_evidence(
        self, tool_name: str, result: ToolResult,
    ) -> list[EvidenceRef]:
        """Extract structured evidence from tool result.

        In MVP: simple excerpt extraction. In production: LLM-based extraction.
        """
        refs: list[EvidenceRef] = []
        for item in result.data.get("results", []):
            refs.append(
                EvidenceRef(
                    source_url=item.get("url", ""),
                    title=item.get("title", ""),
                    excerpt=item.get("snippet", "")[:500],
                    facts=[item.get("snippet", "")],
                    reliability_score=0.7,
                )
            )
        return refs
```

### 4.5 Mock Tool Implementation

```python
class MockWebSearch:
    """Deterministic mock for web_search tool."""

    name = "web_search"
    description = "Search the web for information"

    def __init__(self, results: dict[str, list[dict[str, str]]] | None = None) -> None:
        self._results = results or {
            "postgresql": [
                {
                    "url": "https://example.com/postgresql-guide",
                    "title": "PostgreSQL Guide",
                    "snippet": "PostgreSQL is a powerful, open source object-relational database system.",
                },
            ],
        }
        self.call_history: list[dict[str, Any]] = []

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        query = params.get("query", "")
        self.call_history.append(params)

        results = self._results.get(query.lower(), [])
        return ToolResult(
            success=True,
            data={"results": results, "query": query, "total": len(results)},
            raw_output=f"Found {len(results)} results for '{query}'",
        )
```

---

## 5. Production Readiness

### 5.1 Docker Compose

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-debate}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-debate}
      POSTGRES_DB: ${POSTGRES_DB:-debate}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-debate}"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-debate}:${POSTGRES_PASSWORD:-debate}@db:5432/${POSTGRES_DB:-debate}
      CORS_ORIGINS: http://localhost:3000
      LOG_JSON: "true"
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./apps/api/src:/app/src
      - ./packages:/app/packages
    develop:
      watch:
        - path: ./apps/api/src
          action: sync
        - path: ./packages
          action: sync

  web:
    build:
      context: .
      dockerfile: apps/web/Dockerfile
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - api
    volumes:
      - ./apps/web/src:/app/src
      - ./apps/web/public:/app/public
    develop:
      watch:
        - path: ./apps/web/src
          action: sync

volumes:
  pgdata:
```

### 5.2 Multi-Stage Dockerfile (API)

```dockerfile
# apps/api/Dockerfile
# Stage 1: Install dependencies
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder
WORKDIR /app

# Copy dependency manifests first (layer caching)
COPY apps/api/pyproject.toml apps/api/uv.lock ./
COPY packages/ ../packages/

# Install project dependencies
RUN uv sync --no-dev --no-install-project

# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

# Create non-root user
RUN groupadd -r debate && useradd -r -g debate debate

# Copy from builder
COPY --from=builder /app/.venv /app/.venv
COPY apps/api/src/ /app/src/
COPY packages/ /app/packages/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:/app/packages"

USER debate
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

CMD ["uvicorn", "debate_lab.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.3 Multi-Stage Dockerfile (Web)

```dockerfile
# apps/web/Dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app

COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY apps/web/ ./
RUN pnpm build

# Stage 2: Production
FROM node:20-alpine AS runner
WORKDIR /app

RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

ENV NODE_ENV=production

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
```

### 5.4 Path Aliases & Shared Packages

**Root `tsconfig.base.json`:**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "baseUrl": ".",
    "paths": {
      "@shared/*": ["./packages/*/src"]
    }
  }
}
```

**`apps/web/tsconfig.json`:**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "jsx": "preserve",
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"],
      "@shared/types": ["../../packages/types/src"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"]
}
```

**`apps/web/next.config.ts`:**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@shared/types"],
  output: "standalone",
};

export default nextConfig;
```

### 5.5 Enforcing Server-Side Only in Next.js

```typescript
// apps/web/lib/env.ts
import "server-only";

// This module is guaranteed to never ship to the browser
export const API_SECRET = process.env.API_SECRET!;
export const DATABASE_URL = process.env.DATABASE_URL!;

export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing environment variable: ${name}`);
  return value;
}
```

### 5.6 API Client (TypeScript)

```typescript
// apps/web/lib/api.ts
import { z } from "zod";

// Shared validation schemas (mirrors Pydantic schemas)
const DebateRunSchema = z.object({
  id: z.string().uuid(),
  topic: z.string().min(1),
  status: z.enum(["pending", "running", "complete", "failed"]),
  created_at: z.string().datetime(),
});

const ClaimSchema = z.object({
  id: z.string(),
  text: z.string().min(1),
  agent_id: z.string(),
  status: z.enum([
    "proposed", "challenged", "supported",
    "weakened", "accepted", "unresolved",
  ]),
  evidence_refs: z.array(z.string()),
});

export type DebateRun = z.infer<typeof DebateRunSchema>;
export type Claim = z.infer<typeof ClaimSchema>;

// Typed API client
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}/api/v1${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  getDebateRun: (id: string) =>
    request<DebateRun>(`/debates/${id}`),

  createDebateRun: (input: { topic: string; context: string }) =>
    request<DebateRun>("/debates", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  getClaimGraph: (runId: string) =>
    request<Claim[]>(`/debates/${runId}/claims`),
};
```

---

## Summary of Key Decisions

| Concern | Decision | Rationale |
|---------|----------|-----------|
| Package manager (Python) | `uv` with workspaces | Fast, deterministic lockfile, built-in workspace support |
| Package manager (TS) | `pnpm` + Turborepo | Fast, strict, good monorepo support |
| ORM | SQLAlchemy 2.0 async | Proven, flexible, supports JSONB natively |
| Validation | Pydantic v2 (strict) | `extra="forbid"`, `frozen=True`, field validators |
| Event streaming | SSE via `sse-starlette` | Simpler than WebSocket, auto-reconnect, HTTP-friendly |
| Frontend state | Zustand (client) + TanStack Query (server) | Clear separation of concerns |
| UI components | shadcn/ui | Accessible, customizable, copy-paste model |
| Event store | PostgreSQL JSONB | No extra infra, UNIQUE constraint for concurrency |
| Logging | structlog | Structured, fast, JSON output for log aggregators |
| Testing | pytest-asyncio + Vitest | First-class async support in both ecosystems |
| CI | GitHub Actions | Native, matrix testing, service containers for Postgres |

---

*Generated for DebateLab — last updated July 2026*

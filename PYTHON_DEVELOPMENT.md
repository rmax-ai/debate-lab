# Python Development Guidelines — DebateLab

Day-to-day Python engineering for the DebateLab backend.

---

## Language Version

- **Python 3.12+** required
- `from __future__ import annotations` in all modules
- Use `datetime.now(UTC)` — never `datetime.utcnow()` (deprecated)

## Package Management

```bash
# All packages managed with uv
uv sync --extra dev        # Install all deps including dev
uv add <package>           # Add dependency
uv run pytest tests/ -v    # Run tests
uv run ruff check src/     # Lint
uv run ty check            # Type check
```

## Monorepo Layout

```
debate-lab/
├── apps/
│   ├── web/          # Next.js frontend — NOT Python
│   └── api/          # FastAPI application
│       ├── src/
│       │   └── debate_api/
│       │       ├── __init__.py
│       │       ├── app.py           # FastAPI app factory
│       │       ├── routes/          # REST endpoints
│       │       ├── dependencies.py  # DI wiring
│       │       └── middleware/      # CORS, request-id, error handler
│       ├── tests/
│       └── pyproject.toml
├── packages/
│   ├── orchestrator/   # Debate lifecycle engine
│   ├── harnesses/      # Agent definitions, role prompts
│   ├── tools/          # Tool gateway + implementations
│   ├── tracing/        # Event model, persistence
│   ├── evidence/       # Evidence extraction, scoring
│   └── evals/          # Audit, quality checks
└── pyproject.toml      # Workspace root (optional)
```

**Rules:**
- `packages/` must NOT import from `apps/`
- Domain logic has zero framework dependencies (no FastAPI, no DB imports)
- Each package has a single responsibility
- No circular imports between packages

---

## Data Modeling: Pydantic v2 (Strict Mode)

All agent outputs, event payloads, and API models use Pydantic v2 with strict mode.

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID

class ClaimStatus(str, Enum):
    PROPOSED = "proposed"
    CHALLENGED = "challenged"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    ACCEPTED = "accepted"
    UNRESOLVED = "unresolved"

class Claim(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    id: str = Field(..., pattern=r"^C-\d+$", description="Claim ID, e.g. C-17")
    text: str = Field(..., min_length=1, max_length=2000)
    agent_id: str = Field(..., pattern=r"^[a-z_]+$")
    status: ClaimStatus = ClaimStatus.PROPOSED
    evidence_refs: list[str] = Field(default_factory=list)
    challenged_by: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    revisions: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def _round_confidence(cls, v: float | None) -> float | None:
        if v is not None:
            return round(v, 2)
        return v

class EvidenceRef(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    id: str = Field(..., pattern=r"^E-\d+$")
    source_type: str = Field(..., pattern=r"^(web_search|doc_search|code_search)$")
    url: str | None = None
    title: str = Field(..., min_length=1)
    quote_or_excerpt: str = Field(..., min_length=1)
    extracted_facts: list[str] = Field(default_factory=list)
    reliability_score: float = Field(default=0.5, ge=0.0, le=1.0)
    retrieved_by: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

**Critical rules:**
- `model_config` is a reserved field name — never use it for data
- Use `default_factory` for ALL mutable defaults (lists, dicts, sets)
- Forward references: string annotations + `model_rebuild()` in `__init__.py`
- Every agent output MUST be a Pydantic model — no free text
- `extra = "forbid"` on all models — reject unknown fields

---

## Database: SQLAlchemy 2.0 Async

```python
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime, UTC
import uuid

class Base(DeclarativeBase):
    pass

class DebateRun(Base):
    __tablename__ = "debate_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic: Mapped[str] = mapped_column(String(500))
    context: Mapped[str] = mapped_column(String(5000))
    user_goal: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    selected_agents: Mapped[dict] = mapped_column(JSONB, default=dict)
    rounds_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class DebateRunEvent(Base):
    __tablename__ = "debate_run_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("debate_runs.id"), index=True)
    sequence_number: Mapped[int] = mapped_column()
    event_type: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
```

**Rules:**
- `Mapped[]` type annotations (not legacy `Column()`)
- `UUID` primary keys everywhere
- `JSONB` for event payloads, agent configs
- `TIMESTAMPTZ` always — use `datetime.now(UTC)`
- Alembic for migrations — always generate, never hand-edit

---

## Async Patterns

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Session factory
engine = create_async_engine("postgresql+asyncpg://...", echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# FastAPI dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

# Service pattern
class DebateRunService:
    def __init__(self, db: AsyncSession, event_store: EventStore):
        self.db = db
        self.event_store = event_store

    async def create_run(self, input: DebateInput) -> DebateRun:
        run = DebateRun(topic=input.topic, context=input.context, ...)
        self.db.add(run)
        await self.db.flush()
        await self.event_store.append(run.id, "run_created", actor="system", payload={...})
        return run
```

**Rules:**
- FastAPI routes: `async def` with async DB sessions
- Model calls: `await provider.generate(...)` — never block
- Pure domain logic: synchronous (deterministic, no I/O)
- Phase engine: `async def advance_phase(run, phase)` with event emission

---

## SSE Streaming

Use `sse-starlette` for streaming events to the UI.

```python
from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter
import asyncio
import json

router = APIRouter()

@router.get("/runs/{run_id}/events")
async def stream_events(run_id: UUID):
    async def event_generator():
        event_queue = get_event_queue(run_id)
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield {
                "event": event.event_type,
                "id": str(event.id),
                "data": json.dumps(event.payload),
            }

    return EventSourceResponse(event_generator())
```

---

## Logging: Structlog

```python
import structlog

logger = structlog.get_logger()

# Structured — key-value pairs, never f-strings
logger.info(
    "phase_transition",
    run_id=str(run_id),
    from_phase=current_phase,
    to_phase=next_phase,
)

logger.error(
    "tool_policy_denied",
    run_id=str(run_id),
    agent_id=agent_id,
    tool_name=tool_name,
    reason="budget_exceeded",
)
```

---

## Error Handling

```python
# packages/orchestrator/exceptions.py
class DebateError(Exception):
    """Base for all debate errors."""
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details

class InvalidPhaseTransition(DebateError): ...
class AgentNotFound(DebateError): ...
class ToolPolicyDenied(DebateError): ...
class EvidenceBudgetExceeded(DebateError): ...

# apps/api/src/debate_api/middleware/error_handler.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

async def debate_error_handler(request: Request, exc: DebateError):
    return JSONResponse(
        status_code=400,
        content={
            "error_code": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )
```

---

## Testing

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from debate_api.app import create_app

@pytest.fixture
async def client():
    app = create_app(testing=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# tests/unit/test_phase_engine.py
class TestPhaseEngine:
    def test_valid_transition(self):
        engine = PhaseEngine()
        next_phase = engine.transition("planning", "researching")
        assert next_phase == "researching"

    def test_invalid_transition_raises(self):
        engine = PhaseEngine()
        with pytest.raises(InvalidPhaseTransition):
            engine.transition("pending", "synthesizing")

# tests/integration/test_debate_run.py
@pytest.mark.asyncio
async def test_full_mock_debate(client: AsyncClient):
    response = await client.post("/api/v1/runs", json={
        "topic": "Test topic",
        "context": "Test context",
        "goal": "Test goal",
    })
    assert response.status_code == 201
    run_id = response.json()["id"]
    # Poll until complete
    ...
```

**Rules:**
- Mock providers for all LLM calls in tests
- Mock tool implementations for all tool tests
- Test phase engine as pure functions (no I/O)
- Integration tests: full debate lifecycle with mock agents
- Coverage >80% on packages/

---

## Tooling

```bash
# Format + lint
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/

# Type check
uv run ty check

# Tests
uv run pytest tests/ -v --tb=short
uv run pytest tests/ --cov=packages --cov-report=term-missing

# Run API locally
uv run uvicorn debate_api.app:create_app --reload --port 8000
```

---

## Key Gotchas

- `src/__init__.py` can cause "Source file found twice" — delete it in src-layout packages
- Trailing comma in parenthesized strings creates tuples: `("str",)` ≠ `"str"`
- Pydantic `model_config` is reserved — never name a field after it
- `datetime.utcnow()` is deprecated — use `datetime.now(UTC)`
- `isinstance(x, SomeProtocol)` requires `@runtime_checkable` on the Protocol class
- Frozen Pydantic model mutation: `model_config = {"frozen": True}` prevents attribute assignment. To update fields, load the stored JSON dict, modify it, and write it back.

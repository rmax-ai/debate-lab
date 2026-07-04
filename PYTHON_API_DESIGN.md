# Python API Design Guidelines — DebateLab

RESTful API standards for the DebateLab FastAPI backend.

---

## Route Structure

```
POST   /api/v1/runs              — Create new debate run
GET    /api/v1/runs              — List runs (paginated)
GET    /api/v1/runs/{id}         — Get run status + summary
GET    /api/v1/runs/{id}/events  — SSE event stream
GET    /api/v1/runs/{id}/claims  — Claims for a run
GET    /api/v1/runs/{id}/report  — Final report (when complete)
GET    /api/v1/harnesses         — List available agent harnesses
GET    /api/v1/presets           — List agent presets
```

---

## Request/Response Models

### POST /api/v1/runs

```python
class CreateRunRequest(BaseModel):
    """Request to create a new debate run."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        json_schema_extra={
            "example": {
                "topic": "Should we use Slack as an operational input?",
                "context": "Our company uses Slack heavily...",
                "goal": "Produce an architectural recommendation",
                "maxRounds": 3,
                "preset": "technical_decision",
            }
        },
    )

    topic: str = Field(..., min_length=1, max_length=500)
    context: str = Field(default="", max_length=5000)
    goal: str = Field(..., min_length=1, max_length=1000)
    constraints: str = Field(default="", max_length=2000)
    max_rounds: int = Field(default=3, ge=1, le=5)
    preset: str = Field(default="technical_decision", pattern=r"^[a-z_]+$")

class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic: str
    context: str
    user_goal: str
    status: str
    selected_agents: list[AgentHarnessSummary]
    rounds_count: int
    created_at: datetime
    updated_at: datetime
```

### Claims

```python
class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    agent_id: str
    status: str
    evidence_refs: list[str]
    challenged_by: list[str]
    objections: list[str]
    confidence: float | None = None
```

### Final Report

```python
class ReportResponse(BaseModel):
    run_id: UUID
    executive_synthesis: str
    topic: str
    agents: list[str]
    strongest_claims: list[ClaimResponse]
    challenged_claims: list[ClaimResponse]
    agreements: list[str]
    disagreements: list[str]
    what_changed: list[str]
    final_recommendation: str
    trade_offs: list[TradeOffItem]
    implementation_path: str
    risks: list[str]
    open_questions: list[str]

class TradeOffItem(BaseModel):
    decision: str
    pros: list[str]
    cons: list[str]
```

---

## Error Responses

```python
class APIError(BaseModel):
    """Every error response follows this shape."""
    error_code: str    # machine-readable slug
    message: str       # human-readable description
    details: dict | None = None

# Error codes:
#   "not_found"              — run/agent/claim doesn't exist
#   "validation_error"       — input failed Pydantic validation
#   "invalid_transition"     — phase transition not allowed
#   "tool_policy_denied"     — agent tried unauthorized tool
#   "budget_exceeded"        — tool call or evidence budget hit
#   "run_already_complete"   — can't modify finished run
```

---

## FastAPI App Factory

```python
# apps/api/src/debate_api/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from debate_api.routes import runs, events, harnesses
from debate_api.middleware.error_handler import debate_error_handler
from debate_api.middleware.request_id import RequestIDMiddleware
from debate_orchestrator.exceptions import DebateError

def create_app(testing: bool = False) -> FastAPI:
    app = FastAPI(
        title="DebateLab API",
        version="0.1.0",
        docs_url="/docs" if not testing else None,
    )

    # Middleware (order matters)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(DebateError, debate_error_handler)

    # Routes
    app.include_router(runs.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")
    app.include_router(harnesses.router, prefix="/api/v1")

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
```

---

## Route Example

```python
# apps/api/src/debate_api/routes/runs.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from debate_api.dependencies import get_db, get_orchestrator
from debate_api.schemas import CreateRunRequest, RunResponse
from debate_orchestrator.engine import Orchestrator

router = APIRouter(prefix="/runs", tags=["runs"])

@router.post("", status_code=201, response_model=RunResponse)
async def create_run(
    request: CreateRunRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)],
) -> RunResponse:
    run = await orchestrator.create_run(request)
    return RunResponse.model_validate(run)

@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunResponse:
    run = await db.get(DebateRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse.model_validate(run)

@router.get("/{run_id}/claims", response_model=list[ClaimResponse])
async def get_claims(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ClaimResponse]:
    claims = await claim_service.get_by_run(run_id)
    return [ClaimResponse.model_validate(c) for c in claims]

@router.get("/{run_id}/report", response_model=ReportResponse)
async def get_report(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportResponse:
    run = await db.get(DebateRun, run_id)
    if not run or run.status != "complete":
        raise HTTPException(status_code=404, detail="Report not available")
    return ReportResponse.model_validate(run.final_report)
```

---

## Dependency Injection

```python
# apps/api/src/debate_api/dependencies.py
from collections.abc import AsyncGenerator
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from debate_tracing.event_store import PostgresEventStore, EventEmitter
from debate_orchestrator.engine import Orchestrator
from debate_harnesses.providers import MockModelProvider
from debate_tools.gateway import ToolGateway
from debate_evidence.extractor import EvidenceExtractor

# DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

DbSession = Annotated[AsyncSession, Depends(get_db)]

# Orchestrator
async def get_orchestrator(
    db: DbSession,
) -> Orchestrator:
    event_store = PostgresEventStore(db)
    emitter = EventEmitter(event_store)
    provider = MockModelProvider()
    gateway = ToolGateway(policy=tool_policy, extractor=EvidenceExtractor(), emitter=emitter)
    return Orchestrator(
        event_store=event_store,
        emitter=emitter,
        provider=provider,
        tool_gateway=gateway,
    )

OrchestratorDep = Annotated[Orchestrator, Depends(get_orchestrator)]
```

---

## SSE Event Stream

```python
# apps/api/src/debate_api/routes/events.py
import asyncio
import json
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from uuid import UUID

router = APIRouter(prefix="/runs", tags=["events"])

@router.get("/{run_id}/events")
async def stream_events(run_id: UUID):
    queue = get_or_create_queue(run_id)

    async def event_generator():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                if event is None:  # Sentinel for "stream done"
                    break
                yield {
                    "event": event.get("event_type", "message"),
                    "id": str(event.get("id", "")),
                    "data": json.dumps(event.get("payload", {})),
                }
        except asyncio.TimeoutError:
            pass  # Keep-alive: client reconnects

    return EventSourceResponse(event_generator())
```

---

## Pagination

```python
class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

class PaginatedRunsResponse(BaseModel):
    items: list[RunResponse]
    total: int
    offset: int
    limit: int
```

---

## Versioning

- URL prefix: `/api/v1/`
- Backward compatibility: v1 stays available during v2 development
- Schema evolution: additive only (new fields, never remove existing)
- Deprecation: add `Deprecation: true` header + docs before removal

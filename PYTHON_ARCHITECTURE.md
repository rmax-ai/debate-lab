# Python Architecture Guidelines — DebateLab

Monorepo structure, event sourcing, component boundaries for the DebateLab backend.

Adapted from the general Python architecture standards with DebateLab-specific patterns.

---

## Monorepo Structure

```
debate-lab/
├── apps/
│   ├── api/                    # FastAPI application (deployable)
│   │   ├── src/debate_api/
│   │   │   ├── __init__.py
│   │   │   ├── app.py          # create_app() factory
│   │   │   ├── routes/
│   │   │   │   ├── runs.py     # POST /runs, GET /runs/{id}
│   │   │   │   └── events.py   # GET /runs/{id}/events (SSE)
│   │   │   ├── dependencies.py # DI wiring
│   │   │   └── middleware/
│   │   │       ├── cors.py
│   │   │       ├── request_id.py
│   │   │       └── error_handler.py
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── conftest.py
│   │   └── pyproject.toml
│   └── web/                    # Next.js app — separate package.json
├── packages/
│   ├── orchestrator/           # Core debate engine
│   │   ├── src/debate_orchestrator/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py       # run_debate() main loop
│   │   │   ├── phase_engine.py # State machine, transitions
│   │   │   ├── convergence.py  # Convergence detection
│   │   │   └── types.py        # DebateInput, DebateOutput
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── harnesses/              # Agent definitions
│   │   ├── src/debate_harnesses/
│   │   │   ├── __init__.py
│   │   │   ├── registry.py     # Load/persist harness defs
│   │   │   ├── presets.py      # Technical decision, security review, etc.
│   │   │   ├── providers.py    # ModelProvider protocol + implementations
│   │   │   └── schemas.py      # AgentHarness, HarnessRegistry schemas
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── tools/                  # Tool gateway
│   │   ├── src/debate_tools/
│   │   │   ├── __init__.py
│   │   │   ├── gateway.py      # ToolGateway with policy enforcement
│   │   │   ├── policy.py       # ToolPolicy, budget checks
│   │   │   ├── web_search.py   # MockWebSearch, WebSearch
│   │   │   └── schemas.py      # ToolRequest, ToolResult
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── tracing/                # Event sourcing
│   │   ├── src/debate_tracing/
│   │   │   ├── __init__.py
│   │   │   ├── event_store.py  # PostgresEventStore
│   │   │   ├── models.py       # DebateRunEvent ORM
│   │   │   ├── replay.py       # Reconstruct state from events
│   │   │   └── emitter.py      # SSE event emission
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── evidence/               # Evidence extraction
│   │   ├── src/debate_evidence/
│   │   │   ├── __init__.py
│   │   │   ├── extractor.py    # Extract EvidenceRefs from tool results
│   │   │   ├── scorer.py       # Reliability scoring
│   │   │   └── linker.py       # Claim-to-evidence linking
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── evals/                  # Audit + quality
│       ├── src/debate_evals/
│       │   ├── __init__.py
│       │   ├── auditor.py      # Evidence audit pass
│       │   └── quality.py      # Debate quality metrics
│       ├── tests/
│       └── pyproject.toml
├── docs/                       # Architecture, threat model, research
├── docker/                     # Dockerfiles
├── docker-compose.yml
├── AGENTS.md
├── PYTHON_DEVELOPMENT.md
├── TYPESCRIPT_DEVELOPMENT.md
└── README.md
```

**Rules:**
- `packages/` must NOT import from `apps/` (framework dependency direction)
- Domain logic (orchestrator, evidence, evals) has zero framework deps
- Infrastructure (tracing, tools) may import SQLAlchemy, httpx, etc.
- Each package has `src/<package>/` layout with `py.typed` marker
- Each package has its own `pyproject.toml` with `[tool.hatch.build.targets.wheel]`

---

## Three-Tier Separation

```
┌─────────────────────────────────────────┐
│  Presentation Layer (apps/api/)         │
│  FastAPI routes, middleware, DI         │
│  Thin handlers → delegate to services   │
│  SSE streaming via sse-starlette        │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Domain / Service Layer (packages/)     │
│  orchestrator/  — debate lifecycle      │
│  evidence/      — extraction, scoring   │
│  evals/         — audit, quality        │
│  harnesses/     — agent definitions     │
│  Zero framework deps                    │
│  Pure functions where possible          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Infrastructure Layer (packages/)       │
│  tracing/  — Postgres event store       │
│  tools/    — web search, tool gateway   │
│  harnesses/providers.py — LLM adapters  │
│  SQLAlchemy, httpx, external APIs       │
└─────────────────────────────────────────┘
```

---

## Event Sourcing Architecture

```
User Input
    │
    ▼
┌──────────────────┐
│  Orchestrator    │  Creates run, selects agents
│  (engine.py)     │
└────────┬─────────┘
         │ Emits: run_created, agents_selected
         ▼
┌──────────────────┐
│  Phase Engine    │  Advances phases deterministically
│  (phase_engine)  │
└────────┬─────────┘
         │ Emits: phase_transition, research_plan_created
         ▼
┌──────────────────┐
│  Tool Gateway    │  Policy check → execute → extract evidence
│  (gateway.py)    │
└────────┬─────────┘
         │ Emits: tool_call_requested, tool_call_completed, evidence_extracted
         ▼
┌──────────────────┐
│  Event Store     │  Append immutable event to Postgres
│  (event_store.py)│
└────────┬─────────┘
         │
    ┌────▼────┐
    │Postgres │  debate_run_events table (JSONB payload)
    └────┬────┘
         │
    ┌────▼────────┐
    │SSE Emitter   │  Push to connected UI clients
    │(emitter.py)  │
    └─────────────┘
```

**Event flow rules:**
- Events are append-only, never updated
- Each event has a monotonically increasing `sequence_number` per run
- UI state is derived by replaying events in sequence order
- Replay: `SELECT * FROM debate_run_events WHERE run_id = $1 ORDER BY sequence_number`
- No mutable state tables for run progress — all derived from event log

---

## Phase Engine (State Machine)

```python
# packages/orchestrator/src/debate_orchestrator/phase_engine.py

from enum import StrEnum

class Phase(StrEnum):
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

VALID_TRANSITIONS: dict[Phase, set[Phase]] = {
    Phase.PENDING: {Phase.PLANNING, Phase.FAILED},
    Phase.PLANNING: {Phase.RESEARCHING, Phase.FAILED},
    Phase.RESEARCHING: {Phase.ARGUING, Phase.FAILED},
    Phase.ARGUING: {Phase.CHALLENGING, Phase.FAILED},
    Phase.CHALLENGING: {Phase.REVISING, Phase.SYNTHESIZING, Phase.FAILED},
    Phase.REVISING: {Phase.CHALLENGING, Phase.SYNTHESIZING, Phase.FAILED},
    Phase.SYNTHESIZING: {Phase.AUDITING, Phase.FAILED},
    Phase.AUDITING: {Phase.COMPLETE, Phase.FAILED},
    Phase.COMPLETE: set(),
    Phase.FAILED: set(),
}

class InvalidPhaseTransition(Exception):
    def __init__(self, current: Phase, target: Phase):
        super().__init__(f"Cannot transition from {current} to {target}")

def transition(current: Phase, target: Phase) -> Phase:
    """Pure function — no side effects."""
    if target not in VALID_TRANSITIONS.get(current, set()):
        raise InvalidPhaseTransition(current, target)
    return target
```

---

## Tool Gateway Pattern

```python
# packages/tools/src/debate_tools/gateway.py

class ToolGateway:
    """Mediates all agent tool access with policy enforcement."""

    def __init__(
        self,
        policy: ToolPolicy,
        evidence_extractor: EvidenceExtractor,
        event_emitter: EventEmitter,
    ):
        self.policy = policy
        self.extractor = evidence_extractor
        self.emitter = event_emitter

    async def execute(
        self,
        run_id: UUID,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
    ) -> ToolResult:
        # 1. Policy check
        if not self.policy.is_allowed(agent_id, tool_name):
            raise ToolPolicyDenied(agent_id, tool_name)

        if self.policy.is_budget_exceeded(run_id, agent_id):
            raise EvidenceBudgetExceeded(agent_id)

        # 2. Emit request event
        await self.emitter.emit(run_id, "tool_call_requested", actor=agent_id, payload={
            "tool_name": tool_name,
            "params": params,
        })

        # 3. Execute tool
        result = await self._dispatch(tool_name, params)

        # 4. Extract evidence
        evidence = await self.extractor.extract(result, retrieved_by=agent_id)

        # 5. Emit completion events
        await self.emitter.emit(run_id, "tool_call_completed", actor=agent_id, payload={
            "tool_name": tool_name,
            "result_summary": result.summary,
        })
        for ref in evidence:
            await self.emitter.emit(run_id, "evidence_extracted", actor=agent_id, payload={
                "evidence_ref": ref.model_dump(),
            })

        # 6. Return result
        return ToolResult(data=result.data, evidence_refs=[e.id for e in evidence])
```

---

## Deployment (Docker Compose)

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: debatelab
      POSTGRES_PASSWORD: debatelab
      POSTGRES_DB: debatelab
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://debatelab:debatelab@postgres:5432/debatelab
    depends_on:
      - postgres

  web:
    build:
      context: apps/web
      dockerfile: ../../docker/Dockerfile.web
    ports:
      - "3000:3000"
    environment:
      API_URL: http://api:8000
    depends_on:
      - api

volumes:
  pgdata:
```

---

## Key Non-Negotiables

1. No framework dependencies in domain packages (orchestrator, evidence, evals)
2. No `dict[str, Any]` in public interfaces — use Pydantic models
3. No mutable state — events are the source of truth
4. No hand-edited migration files
5. No production tracebacks in error responses
6. No circular imports between packages
7. `packages/` never imports from `apps/`

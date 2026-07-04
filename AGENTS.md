# AGENTS.md – Guidelines for DebateLab

This document captures the conventions and guidelines that all contributors
and AI coding agents should follow when working on DebateLab.

---

## 1. Project DNA

DebateLab is a traceable multi-agent deliberation workbench — not a chatbot.
The core product is a deterministic orchestration layer that selects specialized
debate agents, lets them use tools under policy, records every claim/tool
call/evidence link, and produces an auditable final synthesis.

**Product principle:** Optimize for claim quality, evidence quality, visible
disagreement, explicit revision, auditable synthesis, and decision usefulness.
Do not optimize for "agents talking."

## 2. Repo Structure

```
debate-lab/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── packages/
│   ├── orchestrator/ # Debate lifecycle + phase transitions + convergence
│   ├── harnesses/    # Agent definitions, role prompts, output schemas
│   ├── tools/        # Tool gateway + search implementations
│   ├── tracing/      # Event model, persistence, replay
│   ├── evidence/     # Evidence extraction, source scoring, claim linking
│   └── evals/        # Report quality checks, evidence audit
├── docs/             # Architecture, threat model, roadmap, decisions
├── docker-compose.yml
└── README.md
```

## 3. Architecture Non-Negotiables

- **Event sourcing is the law.** Every state transition, model call, tool call,
  claim extraction, challenge, revision, audit, and synthesis is an immutable event.
  The UI state is derived from the event log — never mutated directly.
- **Claims are first-class.** Every agent output must produce structured claims
  with evidence refs. The transcript is a secondary view.
- **Tools are mediated.** Agents never call tools directly. All tool calls go
  through the Tool Gateway with policy enforcement, logging, and evidence extraction.
- **Mock-first.** Build the full debate lifecycle with mock models and mock tools
  before integrating real LLMs. Validate the trace model and UI first.
- **No write tools in MVP.** All tool access is read-only. Write-capable tools
  come later with explicit authorization.

## 4. Python Conventions (Backend)

- Python 3.12+, managed with `uv`
- `src/` layout per package
- Pydantic v2 with `model_config = {"extra": "forbid"}` for all schemas
- SQLModel or SQLAlchemy 2.0 async for Postgres
- All agent outputs use strict Pydantic schemas — no free-text agent responses
- `ruff` for lint/format, `ty` for type checking
- `pytest` with `pytest-asyncio` for async tests
- See `PYTHON_DEVELOPMENT.md` and `PYTHON_API_DESIGN.md` for full conventions

## 5. TypeScript Conventions (Frontend)

- Next.js 14+ with App Router
- React 18+ with Server Components where possible
- Tailwind CSS + shadcn/ui components
- Zustand for client state, TanStack Query for server state
- SSE via EventSource API for live debate streaming
- See `TYPESCRIPT_DEVELOPMENT.md` for full conventions

## 6. Testing

- **Backend:** pytest with async support. Mock providers for model calls.
  Mock tool implementations for search. Test the full debate lifecycle end-to-end
  with mock agents before real LLM integration.
- **Frontend:** Vitest + React Testing Library. Mock SSE streams for UI testing.
- **Integration:** Docker Compose with real Postgres. Test event persistence
  and replay.

## 7. Mock-First Development

The build sequence is:
1. Event-sourced run engine with mock models
2. Harness registry with mock providers
3. Mock web_search tool through tool gateway
4. Claim extraction from structured agent outputs
5. Full debate lifecycle with all 11 phases
6. UI with mock event streams
7. Real LLM provider adapter (OpenAI/Anthropic)
8. Real web search (Tavily/Exa/Brave)

Validate the trace model and UI before spending tokens on real models.

## 8. Model Provider Abstraction

Use a provider adapter interface:
```python
class ModelProvider(Protocol):
    async def generate(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...
```

Implementations:
- `MockProvider` — returns deterministic responses for testing
- `OpenAIProvider` — OpenAI-compatible API
- `AnthropicProvider` — Anthropic Messages API
- `LiteLLMProvider` — multi-provider via LiteLLM

All providers must accept a Pydantic schema and return a validated instance.
No raw text responses.

## 9. Event Schema

Every event stored in `debate_run_events`:
```sql
CREATE TABLE debate_run_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES debate_runs(id),
    sequence_number INTEGER NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    actor VARCHAR(64),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Event types: `run_created`, `agents_selected`, `research_plan_created`,
`evidence_gathered`, `opening_position`, `claim_extracted`, `claim_challenged`,
`tool_call_requested`, `tool_call_completed`, `evidence_extracted`,
`position_revised`, `convergence_check`, `evidence_audit`, `final_report`,
`run_completed`, `run_failed`.

## 10. Tool Gateway Contract

```python
class ToolGateway:
    async def execute(
        self,
        run_id: UUID,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
    ) -> ToolResult:
        # 1. Policy check (agent allowlist, run budget, per-agent budget)
        # 2. Execute tool
        # 3. Extract evidence refs from result
        # 4. Emit events (tool_call_requested, tool_call_completed, evidence_extracted)
        # 5. Return result
        ...
```

## 11. Claim Schema (Critical)

```python
class ClaimStatus(str, Enum):
    PROPOSED = "proposed"
    CHALLENGED = "challenged"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    ACCEPTED = "accepted"
    UNRESOLVED = "unresolved"

class Claim(BaseModel):
    id: str  # e.g., "C-17"
    text: str
    agent_id: str
    status: ClaimStatus = ClaimStatus.PROPOSED
    evidence_refs: list[str] = []
    challenged_by: list[str] = []
    objections: list[str] = []
    revisions: list[str] = []
    confidence: float | None = None
```

## 12. Phase Transitions

Valid transitions (enforced by orchestrator):
```
Pending → Planning → Researching → Arguing → Challenging → Revising →
Synthesizing → Auditing → Complete
                                                    → Failed (from any state)
```

## 13. References

- `docs/ARCHITECTURE.md` — full system architecture
- `docs/THREAT_MODEL.md` — failure modes and mitigations
- `docs/ROADMAP.md` — phased delivery plan
- `docs/DECISIONS.md` — key architectural decisions
- `PYTHON_DEVELOPMENT.md` — Python day-to-day engineering
- `PYTHON_API_DESIGN.md` — API design conventions
- `PYTHON_ARCHITECTURE.md` — monorepo structure, event sourcing, component boundaries
- `TYPESCRIPT_DEVELOPMENT.md` — frontend conventions

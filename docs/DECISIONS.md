# Decisions

Key architectural decisions for DebateLab.

## Major Assumptions

1. Mock-first development produces a higher-quality product than building against
   real LLMs from day one. The trace model and debate lifecycle are the hard
   engineering problems; model integration is a thin adapter layer.
2. Event sourcing is worth the complexity cost for this domain. Auditability,
   replay, and debugging are core product requirements, not nice-to-haves.
3. A structured debate protocol produces better outputs than free-form
   multi-agent chat. Enforcing claim extraction, evidence linking, and
   explicit position revision prevents performative debate.
4. Users want to inspect reasoning, not just read conclusions. The UI must
   expose claims, evidence, challenges, and revisions — not just a transcript.

## Key Decisions

### D-001: Event Sourcing as Primary Persistence Model
**Chosen:** All state transitions are immutable events. Current state is derived
from the event log. Postgres JSONB for events table.
**Rejected:** Traditional CRUD with mutable state tables. Would lose audit trail
and replay capability.
**Rationale:** Traceability is the core product differentiator. Every claim,
tool call, and position change must be reconstructable.

### D-002: Mock-First Build Sequence
**Chosen:** Build the full debate lifecycle with mock models and mock tools
before integrating real LLMs.
**Rejected:** Building directly against OpenAI/Anthropic APIs.
**Rationale:** Model calls are expensive and slow. Debugging debate protocol
logic against non-deterministic LLM outputs is nearly impossible. Mock providers
give deterministic, fast iteration.

### D-003: Strict Pydantic Output Schemas for All Agent Outputs
**Chosen:** Every agent output (opening position, challenge, revision) is a
Pydantic model, not free text.
**Rejected:** Allowing agents to produce unstructured text that is later parsed.
**Rationale:** Unstructured parsing is fragile. Structured outputs guarantee
that claims, evidence refs, and revisions are machine-readable from the moment
they're produced.

### D-004: Tool Gateway as Mandatory Mediator
**Chosen:** Agents never call tools directly. All tool calls go through the
Tool Gateway with policy enforcement, logging, and evidence extraction.
**Rejected:** Direct tool access with post-hoc logging.
**Rationale:** Tool governance is a competitive differentiator. The gateway
enforces budgets, allowlists, and evidence extraction at the boundary.

### D-005: Separate Evidence Extractor from Tool Gateway
**Chosen:** Tool results pass through a dedicated Evidence Extractor that
produces structured EvidenceRef objects.
**Rejected:** Having tool implementations self-report evidence.
**Rationale:** Tool implementations should focus on retrieving data. Evidence
extraction (scoring, excerpt selection, fact extraction) is a separate concern
that benefits from a unified pipeline.

### D-006: Monorepo with apps/ and packages/ Separation
**Chosen:** Monorepo with `apps/web`, `apps/api`, and `packages/*` for shared
libraries.
**Rejected:** Separate repos for frontend and backend.
**Rationale:** Tight coupling between event schema (shared), API types (shared),
and UI rendering. A monorepo keeps schema changes synchronized. The packages
directory isolates reusable logic from deployment artifacts.

### D-007: SSE over WebSocket for MVP
**Chosen:** Server-Sent Events for streaming debate events to the UI.
**Rejected:** WebSocket with a library like Socket.IO.
**Rationale:** SSE is simpler, works through HTTP proxies, auto-reconnects, and
is sufficient for unidirectional event streaming. WebSocket is overkill when
the client doesn't need to send events back.

### D-008: Postgres JSONB for Events, Not a Dedicated Event Store
**Chosen:** Postgres with a JSONB `payload` column on `debate_run_events`.
**Rejected:** Dedicated event store (EventStoreDB, Kafka).
**Rationale:** Postgres is already required for structured data. JSONB gives
schema flexibility for evolving event payloads. A dedicated event store adds
operational complexity without benefit at MVP scale.

### D-009: Single Worker, No Queue for MVP
**Chosen:** Single asyncio worker per debate run. No Redis, no task queue.
**Rejected:** Celery/Redis/background job queue.
**Rationale:** MVP supports one debate run at a time. Adding a queue adds
infrastructure complexity. When multi-tenancy arrives, add a proper queue.

### D-010: Provider Adapter Interface with Mock First
**Chosen:** `ModelProvider` protocol with `MockProvider`, `OpenAIProvider`,
`AnthropicProvider` implementations.
**Rejected:** Direct LiteLLM integration from day one.
**Rationale:** The adapter interface is the stable contract. Mock provider
enables deterministic testing. LiteLLM can be added as an implementation
without changing the interface.

## Known Limitations

- Single-tenant only in MVP. No user authentication or session isolation.
- No write-capable tools. All tool access is read-only.
- No persistence of agent conversation context across runs. Each run is isolated.
- Mock models produce deterministic but unrealistic outputs. Real LLM behavior
  (hallucination, prompt sensitivity) is untested in MVP.
- SSE streaming to multiple clients not tested at scale. Single-user assumption.
- No cost enforcement at mock stage. Real cost tracking added with real models.

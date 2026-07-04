# DebateLab — System Architecture

## Executive Summary

DebateLab is a traceable multi-agent deliberation workbench for AI-assisted research and technical decision-making. Its core thesis is that model disagreement, tool use, evidence gathering, critique, revision, and synthesis should be first-class, inspectable system events — not opaque token streams from a single chat. By structuring deliberation as multi-agent debate over an immutable event log, with claims explicitly linked to evidence, and every phase independently auditable, DebateLab transforms model output from a black-box answer into a transparent reasoning record. The system replaces a single "helpful assistant" with a panel of specialized agents (advocate, skeptic, reviewer, synthesizer) who research independently, argue under structured rules, revise positions when challenged, and produce a synthesized recommendation with all supporting traces exposed.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Next.js / React / Tailwind / shadcn-ui                        │ │
│  │  ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌────────┐ ┌───────┐  │ │
│  │  │ Live │ │Agent │ │ Claims │ │Evid. │ │Tool    │ │Report │  │ │
│  │  │Stream│ │Panel │ │ Graph  │ │Table │ │Calls   │ │Export │  │ │
│  │  └──┬───┘ └──────┘ └───┬────┘ └──────┘ └───┬────┘ └───────┘  │ │
│  │     └──────────────────┴────────────────────┘                  │ │
│  │                        │ SSE / REST                            │ │
│  └────────────────────────┼───────────────────────────────────────┘ │
└───────────────────────────┼──────────────────────────────────────────┘
                            │
┌───────────────────────────┼──────────────────────────────────────────┐
│  ┌────────────────────────┴────────────────────────────────────────┐ │
│  │                    FastAPI Backend                               │ │
│  │                                                                  │ │
│  │  ┌──────────────────────┐   ┌──────────────────────────────┐   │ │
│  │  │    DebateEndpoint    │   │   SSE Event Stream Endpoint  │   │ │
│  │  └──────────┬───────────┘   └──────────────┬───────────────┘   │ │
│  │             │                              │                    │ │
│  │  ┌──────────▼─────────────────────────────────────────────┐    │ │
│  │  │              Debate Orchestrator                        │    │ │
│  │  │  ┌────────────────────────────────────────────────────┐ │    │ │
│  │  │  │     Phase Engine (state machine — 11 phases)      │ │    │ │
│  │  │  │  Intake → Selection → Plan → Research → Positions  │ │    │ │
│  │  │  │  → CrossExam → Rebuttal → Revision → Synthesis    │ │    │ │
│  │  │  │  → Audit → Report                                 │ │    │ │
│  │  │  └────────────────────────────────────────────────────┘ │    │ │
│  │  └──────────┬──────────────────────────────────────────────┘    │ │
│  │             │                                                    │ │
│  │  ┌──────────▼──────────────────────────────────────────────┐    │ │
│  │  │     Agent Harness Registry                              │    │ │
│  │  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────┐  │    │ │
│  │  │  │Advocate │ │  Skeptic │ │Reviewer │ │ Synthesizer │  │    │ │
│  │  │  │Harness  │ │  Harness  │ │Harness  │ │   Harness   │  │    │ │
│  │  │  └────┬────┘ └────┬─────┘ └────┬────┘ └──────┬──────┘  │    │ │
│  │  └───────┼────────────┼────────────┼─────────────┼─────────┘    │ │
│  │          │            │            │             │               │ │
│  │  ┌───────▼────────────▼────────────▼─────────────▼────────┐    │ │
│  │  │                  Tool Gateway                           │    │ │
│  │  │  ┌───────────┐ ┌───────────────┐ ┌────────────────┐   │    │ │
│  │  │  │ Policy    │ │  Tool Executor│ │ Evidence       │   │    │ │
│  │  │  │ Checker   │ │  (web/local/  │ │ Extractor      │   │    │ │
│  │  │  │           │ │  gh repos)    │ │                │   │    │ │
│  │  │  └───────────┘ └───────────────┘ └────────────────┘   │    │ │
│  │  └────────────────────────────────────────────────────────┘    │ │
│  │             │                                                    │ │
│  │  ┌──────────▼──────────────────────────────────────────────┐    │ │
│  │  │     Claim Tracker & Claim Graph Engine                  │    │ │
│  │  └─────────────────────────────────────────────────────────┘    │ │
│  │             │                                                    │ │
│  │  ┌──────────▼──────────────────────────────────────────────┐    │ │
│  │  │     Synthesis Engine    │     Eval/Audit Engine         │    │ │
│  │  └─────────────────────────┴───────────────────────────────┘    │ │
│  │                                                                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                            │                                           │
│  ┌─────────────────────────┼───────────────────────────────────────┐  │
│  │                         ▼                                        │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │              PostgreSQL Database                           │  │  │
│  │  │  ┌──────────────┐ ┌──────────────────┐ ┌───────────────┐  │  │  │
│  │  │  │ debate_runs  │ │ debate_run_events│ │ claim_graph   │  │  │  │
│  │  │  │ agents       │ │ (event sourcing) │ │ evidence_refs │  │  │  │
│  │  │  │ harnesses    │ └──────────────────┘ └───────────────┘  │  │  │
│  │  │  └──────────────┘                                         │  │  │
│  │  │  ┌──────────────────┐  ┌───────────────────┐              │  │  │
│  │  │  │ artifact_store   │  │ report_cache      │              │  │  │
│  │  │  │ (JSONB / object) │  │ (generated docs)   │             │  │  │
│  │  │  └──────────────────┘  └───────────────────┘              │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Debate Orchestrator (`packages/orchestrator`)

The central state machine that drives a debate run through its 11 phases. Responsibilities:

- Parse user intake (topic, context, goal, constraints, output format)
- Select agent harnesses from registry based on topic/goal
- Assign roles to each agent (Advocate, Skeptic, Reviewer, etc.)
- Execute phases sequentially with phase-specific logic
- Manage concurrency: parallel independent work (research, positions), sequential dependent work (cross-examination follows positions)
- Emit typed events to the event store at every step
- Enforce convergence detection (agents stop revising when positions stabilize)
- Accept and route tool requests through the Tool Gateway
- Coordinate the final handoff to Synthesis Engine and Audit Engine

### 2. Agent Harness Registry (`packages/harnesses`)

A registry of agent definitions. Each harness specifies:

- **Model**: LLM provider and model name (via LiteLLM or direct provider SDK)
- **Role prompt**: System prompt establishing the agent's persona, stance, and constraints
- **Tools allowlist**: Which tools this agent may invoke (e.g., Advocate may search, Synthesizer may not)
- **Output schema**: Structured Pydantic model for the agent's responses (position statements, claims, revisions)
- **Cost budget**: Maximum tokens/cost per run
- **Evidence budget**: Maximum evidence refs this agent can submit
- **Evaluator**: Optional post-hoc evaluator for this agent's output quality

Built-in agent types for MVP: Advocate, Skeptic, Synthesis Judge. Extensible via harness definition JSON.

### 3. Tool Gateway (`packages/tools`)

The middleware between agents and external tool execution. The request flow:

```
Agent → Tool Request → Orchestrator → Policy Check → Tool Gateway → Tool Executor → Evidence Extractor → Trace Store → Agent
```

Responsibilities:

- **Policy Check**: Verify the tool is in the agent's allowlist; check run-level budget; enforce read-only constraint
- **Tool Execution**: Dispatch to the appropriate tool runtime (web search via Tavily/Exa/Brave, local file search via ripgrep, GitHub search)
- **Evidence Extraction**: From tool results, extract structured EvidenceRef objects (source URL, title, relevant quote, extracted facts, reliability score)
- **Trace Storage**: Log every tool call as an Event in the event store — full input, full output, latency, extracted evidence
- **Rate Limiting**: Per-agent, per-run, and global rate limits on tool calls

### 4. Evidence Extractor (`packages/evidence`)

A focused service that transforms raw tool outputs into structured evidence. Responsibilities:

- Parse search result snippets into `EvidenceRef` objects
- Assign a reliability score based on source type (primary source > secondary > blog > forum)
- Extract salient facts/quotes relevant to the agent's current claim
- Deduplicate evidence refs across agents
- Link evidence to claims via `claim_id` foreign key

### 5. Claim Tracker (`packages/evidence` or dedicated module)

Maintains the claim graph — the structured reasoning backbone. Each `Claim` object tracks:

- **Status lifecycle**: proposed → challenged → supported / weakened / revised → accepted / unresolved
- **Evidence refs**: which EvidenceRef objects support or challenge this claim
- **Objections**: references to other claims or events that challenge it
- **Confidence scoring**: agent-reported confidence, optionally cross-referenced with evidence strength
- **Revision history**: previous versions when an agent revises a claim

The Claim object is _critical_ — without it you only have logs; with it you have inspectable reasoning structure.

### 6. Synthesis Engine (`packages/orchestrator` or separate)

Produces the final report after all debate phases complete. Input: full event log, finalized claim graph, all evidence refs, agent positions and revisions. Output: structured synthesis with deterministic sections:

| Section | Content |
|---------|---------|
| Executive Synthesis | One-paragraph answer recommendation |
| Topic and Context | Restated from intake |
| Agent Panel | Who participated, their roles, models used |
| Evidence Base | All evidence refs with reliability scores |
| Strongest Claims | Claims with high support and weak challenge |
| Challenged Claims | Claims with significant objection |
| Agreements | Where agents converged |
| Disagreements | Where agents diverged (unresolved) |
| What Changed | For each agent: initial → revised position |
| Final Recommendation | The synthesis result |
| Trade-off Table | Pros/cons across options |
| Implementation Path | Concrete steps |
| Risks | Open risks and uncertainties |
| Open Questions | What remains unresolved |
| Full Trace | Link to the event log replay |

### 7. Eval/Audit Engine (`packages/evals`)

A separate, non-participating component that audits the debate after completion. Responsibilities:

- **Evidence audit**: For each claim, verify that cited evidence actually supports the claim (separate LLM call with different prompt)
- **Claim quality evaluation**: Are claims specific, falsifiable, grounded?
- **Debate quality assessment**: Did agents genuinely engage or perform agreement?
- **Hallucination detection**: Cross-reference evidence refs against original sources

This runs as a non-participating "auditor" agent — it does not influence the debate, only evaluates it post-hoc.

---

## Debate Lifecycle — State Machine

```
                        ┌──────────┐
                        │  INTAKE  │
                        └────┬─────┘
                             │
                        ┌────▼─────┐
                        │SELECTION │  ← Agent harnesses chosen based on topic
                        └────┬─────┘
                             │
                        ┌────▼─────┐
                        │  PLAN    │  ← Each agent proposes research plan
                        └────┬─────┘
                             │
                        ┌────▼────────┐
                        │  RESEARCH   │  ← Parallel tool-backed evidence gathering
                        └────┬────────┘
                             │
                        ┌────▼────────┐
                        │  POSITIONS  │  ← Each agent states position with claim IDs
                        └────┬────────┘
                             │
                    ┌────────▼──────────┐
                    │  CROSS-EXAMINATION │  ← Agents challenge each other's claims
                    │  (iterative loop) │
                    └────────┬──────────┘
                             │
                        ┌────▼────────┐
                        │  REBUTTAL   │  ← Tool-backed responses to challenges
                        └────┬────────┘
                             │
                    ┌────────▼─────────┐
                    │  REVISION        │  ← Agents explicitly update positions
                    │  (convergence?)  │
                    └────────┬─────────┘
                             │
                    ┌────────▼──────────┐
                    │  SYNTHESIS         │  ← Synthesizer produces final report
                    └────────┬──────────┘
                             │
                    ┌────────▼────────┐
                    │  AUDIT          │  ← Evidence auditor verifies claims
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  REPORT         │  ← Markdown/JSON export
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  COMPLETE/FAIL  │
                    └─────────────────┘
```

**State transitions**: Each phase has `PENDING → IN_PROGRESS → COMPLETED | FAILED`. The UI's visual status model maps to these states:

```
Pending → Planning → Researching → Arguing → Challenging → Revising → Synthesizing → Auditing → Complete | Failed
```

**Convergence detection**: After each revision cycle, the orchestrator checks whether agent positions have stabilized (no claim status changes, no new challenges). If stable for N rounds or max rounds reached, advance to synthesis.

---

## Data Model

### DebateRun

```python
class DebateRun(Base):
    id: UUID            # primary key
    topic: str          # debate topic from user
    context: str        # additional context/background
    user_goal: str      # what the user wants to achieve
    constraints: str    # constraints on the debate
    status: DebateStatus  # enum: pending | running | complete | failed
    selected_agents: list[AgentHarness]  # agents assigned to this run
    rounds: list[Round]                   # ordered debate rounds
    artifacts: dict      # JSONB: links to generated artifacts
    final_report: str    # markdown report content
    created_at: datetime
    updated_at: datetime
```

### AgentHarness

```python
class AgentHarness(Base):
    id: UUID
    name: str             # e.g., "Distributed Systems Skeptic"
    role: str             # role description for prompt
    model: str            # "gpt-4o" / "claude-3-opus" etc.
    tools_allowed: list[str]  # e.g., ["web_search", "local_docs"]
    policy: str           # tool usage policy text
    instructions: str     # system prompt / role instructions
    cost_budget: float    # max cost for this agent per run
    evidence_budget: int  # max evidence refs per run
    output_schema: dict   # Pydantic JSON schema for structured output
```

### Round

```python
class Round(Base):
    id: UUID
    debate_run_id: UUID   # FK → debate_runs
    phase: PhaseType      # enum: plan | research | positions | cross_exam | rebuttal | revision
    participants: list[UUID]  # agent IDs participating
    events: list[Event]       # ordered events in this round
    started_at: datetime
    ended_at: datetime
```

### Event (Event Sourcing)

```python
class Event(Base):
    id: UUID
    debate_run_id: UUID   # FK → debate_runs
    round_id: UUID        # FK → rounds (nullable for global events)
    type: EventType       # enum: intake | agent_selected | plan_proposed | tool_requested |
                          #        tool_result | position_stated | claim_made | challenge_issued |
                          #        concession | revision_made | synthesis_generated | audit_result | ...
    agent_id: UUID        # FK → agents (nullable for system events)
    parent_event_id: UUID # FK → events (for causal chains, nullable)
    timestamp: datetime
    content: dict         # JSONB: phase-specific payload
    tool_call: ToolCallDetails   # populated if type=tool_requested|tool_result
    evidence_refs: list[EvidenceRef]  # evidence linked to this event
    claims: list[Claim]    # claims involved in this event
```

### Claim

```python
class Claim(Base):
    id: UUID
    text: str             # claim statement
    agent_id: UUID        # FK → agents: who proposed it
    status: ClaimStatus   # enum: proposed | challenged | supported | weakened |
                          #        accepted | unresolved
    evidence_refs: list[EvidenceRef]  # supporting/challenging evidence
    objections: list[Claim]           # claims that challenge this one
    confidence: float     # 0.0–1.0 agent-reported confidence
    revision_of: UUID     # FK → claims: if this claim replaces a previous one
    created_at: datetime
    updated_at: datetime
```

### EvidenceRef

```python
class EvidenceRef(Base):
    id: UUID
    source_type: str      # "web_page" | "local_doc" | "github_repo" | "tool_output"
    url: str              # source URL or file path
    title: str            # document title
    quote_or_excerpt: str # relevant quote
    extracted_facts: list[str]  # key facts extracted
    reliability_score: float    # 0.0–1.0 based on source type and verification
    retrieved_by: UUID    # FK → agents: which agent retrieved this
    timestamp: datetime
```

---

## Event Sourcing Architecture

All system state is derived from the `debate_run_events` table — an append-only log of every action, tool call, claim, and transition that occurred during a debate.

### Why Event Sourcing?

1. **Replayability**: Any debate can be replayed from the event log, step by step, for debugging or analysis
2. **Audit trail**: Every action has a causally-linked parent event, forming a complete provenance graph
3. **UI state derivation**: The live UI stream is a real-time projection of the event log; the Timeline tab replays events in order
4. **Versioning**: Claims, positions, and reports can be traced through revisions
5. **Debugging**: Failed debates can be reconstructed exactly as they happened

### Event Table Schema (PostgreSQL)

```sql
CREATE TABLE debate_run_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debate_run_id   UUID NOT NULL REFERENCES debate_runs(id),
    round_id        UUID REFERENCES rounds(id),
    type            VARCHAR(64) NOT NULL,
    agent_id        UUID REFERENCES agents(id),
    parent_event_id UUID REFERENCES debate_run_events(id),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content         JSONB NOT NULL DEFAULT '{}',
    tool_call       JSONB,  -- nested object
    evidence_refs   JSONB,  -- array of evidence refs
    claims          JSONB,  -- array of claims
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_run_id ON debate_run_events(debate_run_id);
CREATE INDEX idx_events_type ON debate_run_events(type);
CREATE INDEX idx_events_agent ON debate_run_events(agent_id);
CREATE INDEX idx_events_parent ON debate_run_events(parent_event_id);
CREATE INDEX idx_events_timestamp ON debate_run_events(debate_run_id, timestamp);
```

### Replay

```python
async def replay_debate(run_id: UUID) -> DebateRun:
    events = await EventStore.get_events_for_run(run_id)
    run = DebateRun.reconstitute_from_events(events)
    return run
```

The `DebateRun.reconstitute_from_events` method iterates over ordered events and rebuilds the in-memory state: agents, rounds, claims, evidence, status.

---

## Tool Gateway Design

The Tool Gateway is the only path through which agents interact with external systems. All tool use is mediated, logged, and audited.

```
┌─────────┐   Tool Request    ┌──────────────┐
│  Agent   │ ────────────────> │ Orchestrator │
│  Harness │                  │              │
└─────────┘                   └──────┬───────┘
                                     │
                            ┌────────▼────────┐
                            │  Policy Check   │
                            │  ┌────────────┐ │
                            │  │• Agent has │ │
                            │  │ tool in     │ │
                            │  │ allowlist?  │ │
                            │  │• Under run  │ │
                            │  │ budget?     │ │
                            │  │• Read-only? │ │
                            │  │• Rate limit? │ │
                            │  └────────────┘ │
                            └────────┬────────┘
                                     │ deny → return PolicyError as Event
                            ┌────────▼────────┐
                            │  Tool Executor  │
                            │  ┌────────────┐ │
                            │  │• Web Search │ │
                            │  │ (Tavily/Exa)│ │
                            │  │• Local Docs │ │
                            │  │ (ripgrep)   │ │
                            │  │• GitHub     │ │
                            │  │ (future)    │ │
                            │  └────────────┘ │
                            └────────┬────────┘
                                     │ raw result
                            ┌────────▼────────┐
                            │ Evidence        │
                            │ Extractor       │
                            │ ┌─────────────┐ │
                            │ │→ Parse result│ │
                            │ │→ Extract     │ │
                            │ │  facts/quotes│ │
                            │ │→ Assign      │ │
                            │ │  reliability │ │
                            │ │→ Deduplicate │ │
                            │ └─────────────┘ │
                            └────────┬────────┘
                                     │ EvidenceRef[]
                            ┌────────▼────────┐
                            │  Trace Store    │
                            │  → emit Event   │
                            │    type=tool_   │
                            │    result       │
                            └────────┬────────┘
                                     │
                            ┌────────▼────────┐
                            │  Agent Harness  │
                            │  (callback)     │
                            └─────────────────┘
```

### Tool Policies (MVP)

| Policy | Setting |
|--------|---------|
| Default access | Read-only only, no destructive operations |
| Agent allowlists | Per-harness list of permitted tools |
| Run budget | Max N tool calls per debate run (configurable, default 20) |
| Input/output logging | Full capture in event store |
| Source attribution | All tool results tagged with source metadata |
| Write tools | Blocked in MVP (no file modification, no API writes) |

---

## Harness Registry

The registry holds agent definitions that can be selected by the orchestrator. Each harness is a self-contained definition:

```json
{
  "id": "dist-sys-skeptic",
  "name": "Distributed Systems Skeptic",
  "role": "Challenges claims about distributed system architectures, points out failure modes, CAP trade-offs, consistency concerns",
  "model": "gpt-4o",
  "tools_allowed": ["web_search", "local_docs"],
  "policy": "You may search the web and local documents. Critically evaluate all sources. Do not cite without verifying.",
  "cost_budget": 0.05,
  "evidence_budget": 15,
  "output_schema": {
    "type": "object",
    "properties": {
      "position": {"type": "string"},
      "claims": {"type": "array", "items": {"$ref": "#/definitions/Claim"}},
      "supporting_evidence": {"type": "array", "items": {"$ref": "#/definitions/EvidenceRef"}}
    }
  }
}
```

### Built-in Harnesses (MVP)

| Harness | Role | Tools |
|---------|------|-------|
| Advocate | Argues for the recommendation | web_search, local_docs |
| Skeptic | Challenges claims, finds counter-evidence | web_search, local_docs |
| Synthesis Judge | Summarizes and resolves | none (receives only event log) |

---

## Claim Graph

Claims form a directed acyclic graph that represents the debate's reasoning structure:

```
Claim A (proposed by Advocate)
  ├── EvidenceRef 1 (supports A)
  ├── EvidenceRef 2 (supports A)
  ├── Claim B (challenge by Skeptic, status: challenged)
  │     ├── EvidenceRef 3 (supports B)
  │     ├── Claim C (revision of A, weakened by B)
  │     │     ├── EvidenceRef 4 (supports C)
  │     │     └── EvidenceRef 5 (challenges C)
  │     └── Claim D (weakened by B)
  └── Claim E (accepted — unchallenged)
```

Key relationships:
- **supports**: EvidenceRef → Claim (evidence backs a claim)
- **challenges**: Claim → Claim (one claim challenges another)
- **weakens**: Claim → Claim (challenge reduces confidence)
- **revises**: Claim → Claim (replaces a previous version)
- **accepted**: status that survives all challenges
- **unresolved**: status assigned after max rounds without resolution

The UI displays claims as inspectable cards with: claim text, status badge, linked evidence, challenge tree, confidence score, revision history.

---

## API Design

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/debates` | Create a new debate run |
| `GET` | `/api/debates` | List all debate runs |
| `GET` | `/api/debates/{id}` | Get debate run summary |
| `DELETE` | `/api/debates/{id}` | Cancel/delete a debate run |
| `POST` | `/api/debates/{id}/start` | Start a draft debate run |
| `GET` | `/api/debates/{id}/status` | Get current phase and agent states |
| `GET` | `/api/debates/{id}/events` | Get event log (paginated) |
| `GET` | `/api/debates/{id}/claims` | Get claim graph |
| `GET` | `/api/debates/{id}/evidence` | Get all evidence refs |
| `GET` | `/api/debates/{id}/report` | Get final report |
| `GET` | `/api/debates/{id}/trace` | Get full trace bundle (JSON) |
| `GET` | `/api/debates/{id}/events/stream` | SSE stream of live events |
| `GET` | `/api/harnesses` | List available agent harnesses |
| `POST` | `/api/harnesses` | Register a new harness |
| `GET` | `/api/export/{id}.md` | Download markdown report |
| `GET` | `/api/export/{id}.json` | Download JSON trace |

### SSE Event Stream

```typescript
// Client opens SSE connection
const source = new EventSource(`/api/debates/${id}/events/stream`);

// Events are typed Server-Sent Events
source.addEventListener('event', (e) => {
  const event = JSON.parse(e.data);
  // event.type: 'phase_change' | 'agent_action' | 'tool_call' | 'claim_update' | ...
  updateUI(event);
});
```

---

## Deployment Topology (Docker Compose — v1)

```
┌──────────────────────────────────────────────────────────┐
│                     Docker Compose                        │
│                                                           │
│  ┌─────────────────────┐  ┌──────────────────────────┐   │
│  │  nextjs-frontend    │  │  fastapi-backend          │   │
│  │  :3000              │  │  :8000                    │   │
│  │                     │  │                           │   │
│  │  Next.js 14         │  │  FastAPI + uvicorn       │   │
│  │  React 18           │  │  Pydantic models         │   │
│  │  Tailwind CSS       │  │  asyncio workers         │   │
│  │  shadcn/ui          │  │  LiteLLM / provider SDKs │   │
│  │  Zustand/TanQuery   │  │  SQLModel/SQLAlchemy     │   │
│  └──────────┬──────────┘  └───────────┬──────────────┘   │
│             │                         │                    │
│             └───── REST + SSE ────────┘                   │
│                                                           │
│  ┌────────────────────────────────────────────────────┐   │
│  │  postgres:16                                       │   │
│  │  :5432                                             │   │
│  │  debates_db                                        │   │
│  │  Tables: debate_runs, agents, rounds,              │   │
│  │          debate_run_events, claims, evidence_refs   │   │
│  └────────────────────────────────────────────────────┘   │
│                                                           │
│  ┌────────────────────────────────────────────────────┐   │
│  │  minio / local object store                        │   │
│  │  (optional: S3-compatible storage for artifacts)   │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Scaling Constraints (v1)

- Single Docker Compose deployment, no Kubernetes
- FastAPI behind uvicorn with asyncio workers (N=4 default)
- Postgres single instance (no replication)
- Object storage: local filesystem or MinIO
- No horizontal scaling — bounded by single-node resources

---

## Request Lifecycle (End-to-End Flow)

```
User Input
    │
    ▼
1. POST /api/debates { topic, context, goal, constraints, preset }
    │
    ▼
2. Orchestrator creates DebateRun (status=INTAKE)
    │  ├── Parses user input
    │  ├── Emits Event { type: "intake", content: {...} }
    │  └── Status → SELECTION
    │
    ▼
3. Orchestrator selects agents based on preset / topic
    │  ├── Loads AgentHarness definitions from registry
    │  ├── Assigns roles (Advocate, Skeptic, Synthesis Judge)
    │  ├── Emits Event { type: "agent_selected", agents: [...] }
    │  └── Status → PLANNING
    │
    ▼
4. Each agent proposes research plan (parallel)
    │  ├── Agent → "What I need to know, what tools, what claims to test"
    │  ├── Emits Event per agent
    │  └── Status → RESEARCHING
    │
    ▼
5. Independent evidence gathering (parallel, max N tool calls per agent)
    │  ├── Agent → Tool Request → Policy Check → Tool Executor
    │  ├── Evidence Extractor → EvidenceRef objects
    │  ├── Claims extracted from research
    │  └── Each tool call emitted as Event
    │
    ▼
6. Opening positions (parallel)
    │  ├── Each agent: position + claim IDs + evidence refs
    │  ├── Claims registered in Claim Tracker
    │  └── Status → ARGUING
    │
    ▼
7. Cross-examination (iterative, N rounds)
    │  ├── Agents attack each other's claims (not each other)
    │  ├── Responses: concession | counter-evidence | revised claim | unresolved risk
    │  ├── Claim statuses updated: proposed → challenged → supported/weakened
    │  └── Status → CHALLENGING
    │
    ▼
8. Tool-backed rebuttal (parallel, optional)
    │  ├── Agents may request more evidence
    │  ├── Same Tool Gateway flow
    │  └── Status → REVISING
    │
    ▼
9. Revision and concession (parallel)
    │  ├── Each agent explicitly updates position
    │  ├── Convergence detection: stable? → advance
    │  └── Status → SYNTHESIZING
    │
    ▼
10. Synthesis Engine produces final report
    │   ├── Synthesizer receives: event log, claim graph, evidence, positions
    │   ├── Produces deterministic sections
    │   └── Status → AUDITING
    │
    ▼
11. Eval/Audit Engine verifies claims (separate, non-participating)
    │   ├── For each claim: does evidence support it?
    │   ├── Hallucination detection
    │   └── Status → REPORT
    │
    ▼
12. Final report exported (Markdown + JSON trace)
    │   ├── GET /api/debates/{id}/report → Markdown
    │   └── GET /api/debates/{id}/trace → JSON
    │
    ▼
DebateRun status = COMPLETE
```

---

## System Modules

```
debate-lab/
├── apps/
│   ├── web/                    # Next.js frontend
│   │   ├── app/                # Pages and API routes
│   │   ├── components/         # React components
│   │   │   ├── Timeline.tsx
│   │   │   ├── AgentPanel.tsx
│   │   │   ├── LiveStream.tsx
│   │   │   ├── ClaimCard.tsx
│   │   │   ├── ClaimGraph.tsx
│   │   │   ├── EvidenceTable.tsx
│   │   │   ├── ToolCallList.tsx
│   │   │   ├── ReportViewer.tsx
│   │   │   └── DebateStatusBar.tsx
│   │   ├── lib/                # Client utilities
│   │   │   ├── sse-client.ts   # SSE connection manager
│   │   │   └── api-client.ts   # REST client
│   │   └── store/              # Zustand stores
│   │       ├── debate-store.ts
│   │       └── ui-store.ts
│   │
│   └── api/                    # FastAPI backend
│       ├── main.py             # App factory, middleware
│       ├── routers/
│       │   ├── debates.py      # Debate CRUD endpoints
│       │   ├── events.py       # Event stream endpoint
│       │   ├── harnesses.py    # Harness registry endpoints
│       │   └── export.py       # Markdown/JSON export
│       ├── models/
│       │   ├── db.py           # SQLModel ORM models
│       │   ├── schemas.py      # Pydantic request/response schemas
│       │   └── events.py       # Event type definitions
│       └── middleware/
│           └── sse.py          # SSE streaming middleware
│
├── packages/
│   ├── orchestrator/           # Debate state machine
│   │   ├── engine.py           # Phase engine, state transitions
│   │   ├── selection.py        # Agent selection logic
│   │   ├── convergence.py      # Convergence detection
│   │   └── synthesis.py        # Synthesis Engine
│   │
│   ├── harnesses/              # Agent harness definitions
│   │   ├── registry.py         # Harness registry
│   │   ├── base.py             # Base harness class
│   │   ├── advocate.py         # Advocate harness
│   │   ├── skeptic.py          # Skeptic harness
│   │   ├── synthesizer.py      # Synthesis Judge harness
│   │   └── presets.py          # Agent presets (technical, research, product, security)
│   │
│   ├── tools/                  # Tool Gateway
│   │   ├── gateway.py          # Tool Gateway orchestration
│   │   ├── policy.py           # Policy checker
│   │   ├── web_search.py       # Web search (Tavily/Exa/Brave)
│   │   ├── local_search.py     # Local ripgrep-based search
│   │   └── github_search.py    # GitHub search (future)
│   │
│   ├── tracing/                # Event sourcing + trace store
│   │   ├── event_store.py      # Event repository
│   │   ├── replay.py           # Event replay
│   │   └── trace_bundle.py     # Trace export
│   │
│   ├── evidence/               # Evidence extraction + claim tracking
│   │   ├── extractor.py        # Evidence extraction from tool results
│   │   ├── claim_tracker.py    # Claim graph management
│   │   └── reliability.py      # Source reliability scoring
│   │
│   └── evals/                  # Eval/Audit Engine
│       ├── auditor.py          # Evidence auditor
│       ├── hallu_detect.py     # Hallucination detection
│       └── debate_quality.py   # Debate quality assessment
│
├── docs/                       # Documentation
│   ├── SPEC_RAW.md
│   ├── ARCHITECTURE.md
│   └── THREAT_MODEL.md
│
├── docker-compose.yml          # Single Docker Compose deployment
├── Dockerfile.api
├── Dockerfile.web
└── pyproject.toml
```

---

## Risks, Trade-offs, and Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **LLM cost explosion** | Multi-agent, multi-round, tool-heavy debates become expensive | Cost budgets per agent, tool call limits, max round limits, early convergence detection |
| **Latency** | Sequential phases (cross-examination loop) block on LLM calls | Parallel execution where possible; streaming events so UI feels responsive; async workers |
| **Model hallucination in evidence extraction** | Extractor invents facts not in source | Auditor runs separately; confidence scoring; forced quote extraction with source attribution |
| **Agent goal misalignment** | Agents may not correctly play their adversarial role | Structured role prompts with explicit instructions; output schema validation; post-hoc quality eval |
| **Convergence never reached** | Agents keep revising forever | Max rounds hard limit; convergence detection; timeout per phase |

### Trade-offs

| Decision | Trade-off |
|----------|-----------|
| **Event sourcing over state table** | Higher storage costs, more complex queries; but full replay, audit trail, and debuggability |
| **Separate auditor agent** | Additional LLM cost and latency; but prevents circular reasoning within the debate |
| **SQLModel + JSONB** | Less type safety than fully normalized schema; but flexible for evolving event types and nested claim objects |
| **Single Docker Compose** | No horizontal scaling or HA; but vastly simpler deployment for MVP |
| **Read-only tool policy** | Limits use cases (no write-to-doc, no API calling); but eliminates entire class of security threats |

### Open Questions

1. **Should the Synthesis Judge be a separate LLM call or could it be algorithmic aggregation?** — Current design uses LLM; algorithmic aggregation from structured claims is a future optimization.
2. **How granular should the cross-examination loop be?** — Per-claim or per-round? Current design: per-round (agents address multiple claims each round).
3. **Should the evidence auditor run during the debate (halting claims) or after (audit-only)?** — Current design: post-hoc to avoid slowing the debate. Could be phased in as a real-time evidentiary check in v2.
4. **What is the right convergence metric?** — Claim status stability? Agent self-reported satisfaction? Max rounds? Current design: combination of all three.
5. **How do we prevent prompt leakage between agents?** — Each agent's system prompt is isolated; tool results are the only shared context. See threat model.
6. **Should tool call results be shared across agents or kept per-agent?** — Current design: shared evidence store with attribution, so duplicate research is avoided but agents don't see each other's raw research.

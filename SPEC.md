# DebateLab — Specification

## Scope

DebateLab is a traceable multi-agent deliberation workbench. Users enter a topic,
context, and goal; the system selects specialized debate agents, runs structured
debate rounds with tool-backed evidence gathering, and produces an auditable
synthesis report.

The MVP validates the trace model and debate lifecycle with mock models and mock
tools before integrating real LLMs.

## Features

### Event-Sourced Run Engine
- PostgreSQL-backed immutable event log
- Phase state machine (11 phases: Intake → Selection → Planning → Research → Positions → Cross-Exam → Rebuttal → Revision → Synthesis → Audit → Report)
- SSE streaming to connected UI clients
- Replay: reconstruct run state from event log

### Agent Harness Registry
- Agent definitions: model, role, tools_allowed, policy, budgets
- Mock model provider for deterministic testing
- Built-in presets: Technical Decision, Research Article, Product Strategy, Security Review

### Tool Gateway
- Policy enforcement: per-agent allowlists, per-run budgets, per-agent budgets
- Mock web_search implementation
- Evidence extraction from tool results

### Claim Extraction
- Structured claims with status state machine
- Evidence ref linking
- Cross-examination: agents challenge specific claim IDs

### Full Debate Lifecycle
- 11-phase structured debate protocol
- Convergence detection
- Evidence audit pass
- Final synthesis report (Markdown/JSON export)

### Frontend UI
- Debate input form with presets
- Live event stream via SSE
- Tab system: Live, Agents, Claims, Evidence, Tool Calls, Transcript, Report
- Report viewer

## Acceptance Criteria

### Step 1: Event-Sourced Run Engine
- [ ] PostgreSQL schema creates `debate_runs` and `debate_run_events` tables
- [ ] Event store appends events with monotonically increasing sequence numbers
- [ ] Phase state machine enforces valid transitions
- [ ] SSE endpoint streams events to connected clients
- [ ] Replay reconstructs run state from event log
- [ ] All unit + integration tests pass (mock DB)

### Step 2: Harness Registry + Mock Providers
- [ ] AgentHarness model parses and validates
- [ ] MockModelProvider returns deterministic responses matching Pydantic schemas
- [ ] Built-in presets load from definition files
- [ ] Harness registry CRUD works
- [ ] All tests pass

### Step 3: Tool Gateway + Mock Search
- [ ] ToolGateway enforces policy (allowlist, budgets)
- [ ] MockWebSearch returns deterministic results
- [ ] EvidenceExtractor produces EvidenceRef objects from tool results
- [ ] Policy denied and budget exceeded errors are handled gracefully
- [ ] All tests pass

### Step 4: Claim Extraction
- [ ] Claim model with status state machine validates
- [ ] Claim extraction from structured agent outputs works
- [ ] EvidenceRef linking to claims works
- [ ] Claim graph data is queryable
- [ ] All tests pass

### Step 5: Full Debate Lifecycle
- [ ] All 11 phases execute in order with mock agents
- [ ] Cross-examination targets specific claim IDs
- [ ] Agents revise positions after challenges
- [ ] Convergence detection terminates debate early when appropriate
- [ ] Evidence audit pass runs after synthesis
- [ ] Final report exports as Markdown and JSON
- [ ] End-to-end test: full mock debate run completes

### Step 6: Frontend UI
- [ ] Input form submits and creates a run
- [ ] Live event stream renders events in real-time
- [ ] Timeline shows phase progress
- [ ] Agent panel shows active agent status
- [ ] All tabs work: Claims, Evidence, Tool Calls, Transcript, Report
- [ ] Report viewer renders Markdown

### Step 7: Presets + Seed Examples
- [ ] Four agent presets available: Technical Decision, Research Article, Product Strategy, Security Review
- [ ] Seed example: architecture decision debate run
- [ ] Seed example: research article debate run
- [ ] Seed example: security review debate run
- [ ] Docker Compose starts all services

## Non-Goals (MVP)

- Multi-user authentication
- Real LLM integration (mock models only)
- Real web search (mock search only)
- Write-capable tools
- Slack/email/calendar integration
- Long-running background agents
- Complex graph UI for claims

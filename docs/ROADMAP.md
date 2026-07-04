# Roadmap

## v0.1.0 — MVP: Mock-First Core Engine

**Goal:** Full debate lifecycle working end-to-end with mock models and mock
tools. Validate the trace model, event sourcing, and UI before real LLM costs.

### Step 1: Event-Sourced Run Engine
- [ ] PostgreSQL schema: `debate_runs`, `debate_run_events`, `agent_harnesses`
- [ ] Event store: append-only with sequence numbers
- [ ] DebateRun model: create, transition phases, complete/fail
- [ ] Phase state machine with valid transitions
- [ ] SSE streaming: emit events to connected clients
- [ ] Replay: reconstruct run state from event log

### Step 2: Harness Registry + Mock Providers
- [ ] AgentHarness model: id, name, role, model, tools_allowed, policy, instructions, budgets
- [ ] MockModelProvider: returns deterministic responses that match Pydantic schemas
- [ ] Built-in harness presets: Advocate, Skeptic, Synthesizer
- [ ] Harness registry: load from JSON/YAML definitions

### Step 3: Tool Gateway + Mock Search
- [ ] ToolGateway: policy check → execute → extract evidence → emit events → return result
- [ ] ToolPolicy: per-agent allowlist, per-run budget, per-agent budget
- [ ] MockWebSearch: returns deterministic search results
- [ ] Evidence extraction from tool results

### Step 4: Claim Extraction
- [ ] Claim model with status state machine
- [ ] Claim extraction from structured agent outputs
- [ ] EvidenceRef linking to claims
- [ ] Claim graph visualization data

### Step 5: Full Debate Lifecycle
- [ ] Phase 1: Intake — parse user input
- [ ] Phase 2: Agent selection — orchestrator chooses harnesses
- [ ] Phase 3: Research planning — agents propose research plans
- [ ] Phase 4: Evidence gathering — agents use tools under policy
- [ ] Phase 5: Opening positions — structured claims with evidence refs
- [ ] Phase 6: Cross-examination — agents challenge specific claim IDs
- [ ] Phase 7: Tool-backed rebuttal — agents request more evidence
- [ ] Phase 8: Revision and concession — agents update positions
- [ ] Phase 9: Synthesis — synthesizer produces final report
- [ ] Phase 10: Evidence audit — verifier checks claim grounding
- [ ] Phase 11: Final report — Markdown/JSON export

### Step 6: Frontend UI
- [ ] Input form: topic, context, goal, max rounds, agent preset
- [ ] Debate timeline: phase progress with status indicators
- [ ] Live event stream: streaming events via SSE
- [ ] Agent panel: active agent, current task, claims, tool calls
- [ ] Tab system: Live, Agents, Claims, Evidence, Tool Calls, Transcript, Report
- [ ] Report viewer: rendered Markdown final report

### Step 7: Presets + Seed Examples
- [ ] Agent presets: Technical decision, Research article, Product strategy, Security review
- [ ] Seed examples for architecture decision, research article, security review
- [ ] Docker Compose for local development

## v0.2.0 — Real Model Integration

- [ ] OpenAI provider adapter
- [ ] Anthropic provider adapter
- [ ] LiteLLM multi-provider adapter
- [ ] Real web search (Tavily/Exa/Brave)
- [ ] Local document search (ripgrep)
- [ ] GitHub repo search

## v0.3.0 — Evaluation & Quality

- [ ] Single-agent vs debate-agent output comparison rubric
- [ ] Evidence audit improvements
- [ ] Claim quality scoring
- [ ] Cost tracking and budgeting enforcement
- [ ] Performance optimization for multi-agent runs

## Future

- [ ] Multi-user enterprise auth
- [ ] Slack integration (notification surface, not event source)
- [ ] Write-capable tools with explicit authorization
- [ ] Custom harness plugin marketplace
- [ ] Long-running background debate agents
- [ ] Complex graph UI for claim relationships

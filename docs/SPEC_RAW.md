# DebateLab — Raw Specification

## 1. Product Concept

**Working name:** DebateLab: Traceable Multi-Agent Research and Deliberation Workbench

A traceable deliberation harness for AI-assisted research and technical decision-making. It turns model disagreement, tool use, evidence gathering, critique, revision, and synthesis into inspectable system events.

User enters: Topic, Context, Goal, Constraints, Desired output format.

System: Creates debate run → selects agent harnesses → assigns roles → agents gather evidence via tools → structured debate rounds → tracks claims/evidence/objections/concessions → final synthesis → exports trace/report/evidence bundle.

The product should feel like watching a research hearing where every participant has a role, every argument has evidence, and every conclusion can be inspected.

## 2. Core Objects

- **DebateRun**: id, topic, context, user_goal, status, selected_agents, rounds, artifacts, final_report
- **AgentHarness**: id, name, role, model, tools_allowed, policy, instructions, cost_budget, evidence_budget
- **Round**: id, phase, participants, events, started_at, ended_at
- **Event**: id, type, agent_id, parent_event_id, timestamp, content, tool_call, evidence_refs, claims
- **Claim**: id, text, agent_id, status (proposed|challenged|supported|weakened|accepted|unresolved), evidence_refs, objections, confidence
- **EvidenceRef**: id, source_type, url/file/tool/result, title, quote_or_excerpt, extracted_facts, reliability_score, retrieved_by, timestamp

The Claim object is critical — without it you only have logs. With it you have inspectable reasoning structure.

## 3. Debate Lifecycle

11 phases:

1. Intake — user input parsed
2. Agent selection — orchestrator chooses agents based on topic/goal
3. Research planning — each agent proposes what it needs to know, which tools, what claims to test, what would change its mind
4. Independent evidence gathering — agents use tools under policy constraints
5. Opening positions — each agent gives position with claim IDs and evidence refs
6. Cross-examination — agents attack claims (not each other), must answer with concession/counter-evidence/revised claim/unresolved risk
7. Tool-backed rebuttal — agents can request more evidence to support claims
8. Revision and concession — each agent explicitly updates its position
9. Synthesis — synthesizer produces final recommendation, decision rationale, agreements, disagreements, evidence map, risks, evolution path, open questions, implementation plan
10. Evidence audit — separate verifier checks claim grounding
11. Final report — markdown export

## 4. UI Design

Main screen: Timeline (left) | Active Agent Panel (right) | Live Event Stream (bottom)

Tabs: Live | Agents | Claims | Evidence | Tool Calls | Transcript | Report

Visual status model: Pending → Planning → Researching → Arguing → Challenging → Revising → Synthesizing → Auditing → Complete | Failed

## 5. Agent and Harness Design

Harness = model + role prompt + tool policy + output schema + budget + evaluator

Example: Distributed Systems Skeptic, Enterprise Adoption Advocate, Security/Governance Reviewer, Platform Architect, Synthesis Judge

## 6. Tool Calling Model

Agent → Tool Request → Orchestrator → Policy Check → Tool Gateway → Tool Result → Evidence Extractor → Trace Store → Agent

Tool policies: Read-only by default, per-agent allowlists, per-run budget, full input/output logging, source attribution required, no write tools in MVP.

## 7. Traceability Requirements

Minimum trace: user input, selected agents, prompts sent, model outputs, tool calls, tool results, extracted evidence, claims created/challenged, revisions, synthesis prompt, final answer, costs, latency.

Event sourcing via `debate_run_events` table. UI state derived from event log. Enables replay, debugging, audits, evals.

## 8. Backend Architecture

Next.js/React UI ↔ WebSocket/SSE ↔ FastAPI Backend:
- Debate Orchestrator
- Agent Harness Registry
- Tool Gateway
- Evidence Extractor
- Claim Tracker
- Synthesis Engine
- Eval/Audit Engine

Postgres for structured traces. Object storage for raw artifacts. No Kubernetes for v1.

## 9. Debate Engine Pseudocode

async def run_debate(input) → DebateRun with parallel agent steps, cross-examination loops, convergence detection, evidence audit, synthesis, event emission at every step.

## 10. Claim Graph

Claims as structured objects with evidence refs, challenges, objections, revisions, confidence scores. Displayed as inspectable cards in UI.

## 11. Final Report Format

Deterministic sections: Executive synthesis, topic/context, agents, evidence base, strongest claims, challenged claims, agreements, disagreements, what changed, final recommendation, trade-off table, implementation path, risks, open questions, full trace.

## 12. MVP Scope

Input form: topic, context, goal, max rounds, agent preset (Technical decision, Research article, Product strategy, Security review).

Tools: web search, local document search, optional GitHub repo search.

Trace: event stream, tool calls, claims, evidence, final report.

Exports: Markdown, JSON trace.

## 13. Tech Stack

Frontend: Next.js, React, Tailwind, shadcn/ui, Zustand/TanStack Query, SSE for live events.
Backend: Python FastAPI, Pydantic, asyncio workers, LiteLLM or direct provider SDKs, Postgres, SQLModel/SQLAlchemy.
Storage: Postgres JSONB for events, local/S3 object store for artifacts.
Search: Tavily/Exa/Brave for web, ripgrep for local, GitHub search later.
Deployment: single Docker Compose.

## 14. System Modules

apps/web, apps/api, packages/orchestrator, packages/harnesses, packages/tools, packages/tracing, packages/evidence, packages/evals

## 15. Failure Modes

Performative debate, evidence laundering, tool spam, convergence theater, prompt leakage, cost explosion, trace overload.

Mitigations: strict output schemas, claim limits, tool call limits, forced claim-to-evidence mapping, separate evidence auditor, progressive summaries.

## 16. Product Principle

Optimize for: claim quality, evidence quality, visible disagreement, explicit revision, auditable synthesis, decision usefulness.

A good debate run answers: what did each agent believe, why, what evidence, who challenged it, what changed, what remained unresolved, why the final recommendation.

## 17. Concrete Build Sequence

1. Event-sourced run engine
2. Two fixed harnesses (Advocate, Skeptic, Synthesizer)
3. Web search tool
4. Claim extraction
5. Cross-examination
6. Final report
7. Presets

## 18. Positioning

"A traceable deliberation harness for AI-assisted research and technical decision-making."

## 19. Deep Implementation Prompt

Full prompt for code generation covering all technical requirements.

## 20. Next Steps

Build MVP with mock models and mock tools first. Validate trace model and UI before spending tokens. Implement real model adapter only after debate lifecycle works end-to-end.

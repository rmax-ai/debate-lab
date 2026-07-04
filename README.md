# DebateLab

**A traceable deliberation harness for AI-assisted research and technical decision-making.**

DebateLab turns model disagreement, tool use, evidence gathering, critique,
revision, and synthesis into inspectable system events.

It's not a chatbot. It's a research hearing where every participant has a role,
every argument has evidence, and every conclusion can be inspected.

## Quickstart

```bash
# Clone and start
git clone https://github.com/rmax-ai/debate-lab.git
cd debate-lab
docker compose up -d

# Open http://localhost:3000
```

## How It Works

1. **You enter** a topic, context, goal, and constraints
2. **The orchestrator selects** specialized debate agents from a harness registry
3. **Agents research** using read-only tools under policy governance
4. **Structured debate rounds** with claims, evidence, cross-examination, and revision
5. **Final synthesis** with auditable trace of every claim, tool call, and position change

## Architecture

```
User → Next.js/React UI → SSE/REST → FastAPI Backend
                                        ├── Debate Orchestrator
                                        ├── Agent Harness Registry
                                        ├── Tool Gateway
                                        ├── Evidence Extractor
                                        ├── Claim Tracker
                                        ├── Synthesis Engine
                                        └── Eval/Audit Engine
                                              │
                                         Postgres (events, traces)
```

## Key Design Principles

- **Claims are first-class objects**, not just transcript lines
- **Every tool call is mediated** through a policy-enforcing gateway
- **Event sourcing** makes every run replayable and auditable
- **Mock-first development** validates the protocol before real LLM costs
- **Structured outputs** — no free-text agent responses allowed

## Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full system architecture |
| [THREAT_MODEL.md](docs/THREAT_MODEL.md) | Failure modes and mitigations |
| [ROADMAP.md](docs/ROADMAP.md) | Phased delivery plan |
| [DECISIONS.md](docs/DECISIONS.md) | Key architectural decisions |
| [AGENTS.md](AGENTS.md) | Conventions for contributors and AI agents |

## Tech Stack

**Frontend:** Next.js, React, TypeScript, Tailwind CSS, shadcn/ui
**Backend:** Python 3.12+, FastAPI, Pydantic v2, asyncio
**Storage:** PostgreSQL (events, traces), S3-compatible (artifacts)
**Deployment:** Docker Compose

## Status

**v0.1.0 — MVP (in development)**
Mock-first core engine with full debate lifecycle, event sourcing, and UI.

## License

MIT

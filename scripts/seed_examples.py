#!/usr/bin/env python3
"""Seed example: Run a debate programmatically and print the report.

Usage:
    cd packages/orchestrator
    uv run python ../../scripts/seed_examples.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "orchestrator" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "tracing" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "harnesses" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "tools" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "evidence" / "src"))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from debate_orchestrator.engine import Orchestrator
from debate_orchestrator.types import DebateInput
from debate_tracing.emitter import EventEmitter
from debate_tracing.event_store import PostgresEventStore
from debate_tracing.models import Base


EXAMPLES = [
    {
        "name": "Architecture Decision",
        "topic": "Should we use an event bus or Slack for operational signals?",
        "context": (
            "Our company uses Slack heavily for communication, but some workflows "
            "need notifications as operational signals. We need reliability, "
            "auditability, and clear ownership."
        ),
        "goal": "Produce an architectural recommendation for the platform team.",
        "preset": "technical_decision",
        "max_rounds": 2,
    },
    {
        "name": "Security Review",
        "topic": "Is our authentication system adequate for SOC2 compliance?",
        "context": (
            "We use OAuth2 with JWT tokens. Sessions are stored client-side. "
            "We need to assess gaps before our SOC2 audit."
        ),
        "goal": "Identify gaps and recommend improvements.",
        "preset": "security_review",
        "max_rounds": 1,
    },
    {
        "name": "Research Article",
        "topic": "Are microservices always better than monoliths for early-stage startups?",
        "context": (
            "Industry consensus pushes microservices, but many successful startups "
            "started with monoliths. We need evidence-based guidance."
        ),
        "goal": "Evaluate the evidence for and against microservices at early stage.",
        "preset": "research_article",
        "max_rounds": 2,
    },
]


async def run_example(example: dict):
    print(f"\n{'='*60}")
    print(f"  {example['name']}")
    print(f"  Topic: {example['topic']}")
    print(f"{'='*60}")

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        event_store = PostgresEventStore(session)
        emitter = EventEmitter()
        orchestrator = Orchestrator(event_store, emitter)

        debate_input = DebateInput(
            topic=example["topic"],
            context=example["context"],
            goal=example["goal"],
            max_rounds=example["max_rounds"],
            preset=example["preset"],
        )

        report = await orchestrator.run_debate(debate_input)

        print(f"\n  Agents: {len(report['agents'])}")
        print(f"  Claims: {report['claim_stats']['total']}")
        print(f"  Final recommendation: {report['final_recommendation']}")
        print(f"  Agreements: {len(report['agreements'])}")
        print(f"  Disagreements: {len(report['disagreements'])}")
        print(f"  What changed: {len(report['what_changed'])}")

        # Save report
        out_dir = Path(__file__).resolve().parent.parent / "reports"
        out_dir.mkdir(exist_ok=True)
        filename = example["name"].lower().replace(" ", "_")
        report_path = out_dir / f"{filename}.json"
        report_path.write_text(json.dumps(report, indent=2, default=str))
        print(f"\n  Report saved: {report_path}")

    await engine.dispose()


async def main():
    print("DebateLab — Seed Examples")
    print("=" * 60)

    for example in EXAMPLES:
        await run_example(example)

    print(f"\n{'='*60}")
    print("All seed examples complete.")


if __name__ == "__main__":
    asyncio.run(main())

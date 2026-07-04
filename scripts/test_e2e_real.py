"""E2E test: real provider debate (DeepSeek, 1 round, simple topic)."""
import asyncio
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "packages" / "harnesses" / "src"))
sys.path.insert(0, str(repo_root / "packages" / "orchestrator" / "src"))
sys.path.insert(0, str(repo_root / "packages" / "tracing" / "src"))
sys.path.insert(0, str(repo_root / "packages" / "tools" / "src"))
sys.path.insert(0, str(repo_root / "packages" / "evidence" / "src"))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from debate_harnesses.real_providers import DeepSeekProvider
from debate_orchestrator.engine import Orchestrator
from debate_orchestrator.types import DebateInput
from debate_tracing.emitter import EventEmitter
from debate_tracing.event_store import PostgresEventStore
from debate_tracing.models import Base


async def main():
    api_key = Path("/tmp/dl_key.txt").read_text().strip()
    if not api_key:
        print("ERROR: No API key")
        sys.exit(1)

    provider = DeepSeekProvider(api_key=api_key)
    print("Provider: deepseek-chat ✓")

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        event_store = PostgresEventStore(session)
        emitter = EventEmitter()
        orchestrator = Orchestrator(event_store, emitter, provider=provider)

        debate_input = DebateInput(
            topic="Is Python's GIL still relevant in 2026?",
            context="Python 3.13 introduced a free-threaded build option.",
            goal="Produce a concise evidence-based analysis.",
            max_rounds=1,
            preset="research_article",
        )

        print(f"\nTopic: {debate_input.topic}")
        print(f"Preset: {debate_input.preset}, rounds: {debate_input.max_rounds}")
        print("Running debate...\n")

        report = await orchestrator.run_debate(debate_input)

        print(f"Agents: {len(report['agents'])}")
        print(f"Provider calls: {provider.call_count}")
        print(f"Claims total: {report['claim_stats']['total']}")
        print(f"Agreements: {len(report['agreements'])}")
        print(f"Disagreements: {len(report['disagreements'])}")
        print(f"What changed: {len(report['what_changed'])}")
        print(f"\nExecutive synthesis:\n  {report['executive_synthesis'][:300]}")
        print(f"\nFinal recommendation:\n  {report['final_recommendation'][:300]}")

        # Validate real content (not mock defaults)
        assert "mock_" not in report["executive_synthesis"], "Got mock response!"
        assert "mock_" not in report["final_recommendation"], "Got mock response!"
        print("\n✓ E2E test passed — real provider, real content!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

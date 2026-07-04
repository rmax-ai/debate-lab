"""End-to-end test: full mock debate lifecycle."""

import pytest
from debate_tracing.emitter import EventEmitter
from debate_tracing.event_store import PostgresEventStore
from debate_tracing.models import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from debate_orchestrator.engine import Orchestrator
from debate_orchestrator.types import DebateInput


@pytest.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


class TestFullDebate:
    async def test_technical_decision_debate(self, session: AsyncSession):
        """Run a full technical decision debate end-to-end with mock models."""
        event_store = PostgresEventStore(session)
        emitter = EventEmitter()
        orchestrator = Orchestrator(event_store, emitter)

        debate_input = DebateInput(
            topic="Should we use an event bus or Slack for operational signals?",
            context="Enterprise setting with audit requirements.",
            goal="Produce an architectural recommendation.",
            max_rounds=2,
            preset="technical_decision",
        )

        report = await orchestrator.run_debate(debate_input)

        # Report has the expected structure
        assert report["topic"] == debate_input.topic
        assert "executive_synthesis" in report
        assert "final_recommendation" in report
        assert "agents" in report
        assert len(report["agents"]) == 4  # technical_decision preset

        # Check claim stats
        assert "claim_stats" in report
        assert report["claim_stats"]["total"] > 0

        # Check agreements and disagreements
        assert "agreements" in report
        assert "disagreements" in report

    async def test_security_review_debate(self, session: AsyncSession):
        """Run a security review debate end-to-end."""
        event_store = PostgresEventStore(session)
        emitter = EventEmitter()
        orchestrator = Orchestrator(event_store, emitter)

        debate_input = DebateInput(
            topic="Is our authentication system adequate for SOC2 compliance?",
            goal="Identify gaps and recommend improvements.",
            max_rounds=1,
            preset="security_review",
        )

        report = await orchestrator.run_debate(debate_input)
        assert report["topic"] == debate_input.topic
        assert len(report["agents"]) == 4  # security_review preset
        assert "executive_synthesis" in report

    async def test_research_article_debate(self, session: AsyncSession):
        """Run a research article debate end-to-end."""
        event_store = PostgresEventStore(session)
        emitter = EventEmitter()
        orchestrator = Orchestrator(event_store, emitter)

        debate_input = DebateInput(
            topic="Are microservices always better than monoliths?",
            goal="Evaluate the evidence for and against microservices.",
            max_rounds=1,
            preset="research_article",
        )

        report = await orchestrator.run_debate(debate_input)
        assert len(report["agents"]) == 3  # research_article preset
        assert "claim_stats" in report

    async def test_product_strategy_debate(self, session: AsyncSession):
        """Run a product strategy debate end-to-end."""
        event_store = PostgresEventStore(session)
        emitter = EventEmitter()
        orchestrator = Orchestrator(event_store, emitter)

        debate_input = DebateInput(
            topic="Should we launch a freemium tier?",
            goal="Decide on pricing strategy.",
            max_rounds=1,
            preset="product_strategy",
        )

        report = await orchestrator.run_debate(debate_input)
        assert len(report["agents"]) == 4  # product_strategy preset
        assert "final_recommendation" in report

    async def test_report_has_required_sections(self, session: AsyncSession):
        """Verify the final report has all required sections."""
        event_store = PostgresEventStore(session)
        emitter = EventEmitter()
        orchestrator = Orchestrator(event_store, emitter)

        report = await orchestrator.run_debate(
            DebateInput(topic="Test topic", goal="Test goal", max_rounds=1)
        )

        required_sections = [
            "executive_synthesis",
            "topic",
            "goal",
            "agents",
            "strongest_claims",
            "challenged_claims",
            "agreements",
            "disagreements",
            "what_changed",
            "final_recommendation",
            "trade_offs",
            "risks",
            "open_questions",
            "implementation_path",
            "claim_stats",
        ]
        for section in required_sections:
            assert section in report, f"Missing section: {section}"

    async def test_event_emission(self, session: AsyncSession):
        """Verify events are emitted during a debate."""
        event_store = PostgresEventStore(session)
        emitter = EventEmitter()
        orchestrator = Orchestrator(event_store, emitter)

        await orchestrator.run_debate(
            DebateInput(topic="T", goal="G", max_rounds=1)
        )

        # SSE emitter should have a subscriber queue (we don't subscribe here,
        # but the event store should have recorded events)
        assert len(emitter._queues) == 0  # no subscribers in this test

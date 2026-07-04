"""Debate engine — the core run_debate() loop that wires everything together."""

from __future__ import annotations

import uuid
from typing import Any

from debate_evidence.extractor import EvidenceExtractor
from debate_evidence.schemas import ClaimStatus
from debate_harnesses.presets import get_preset
from debate_harnesses.providers import MockModelProvider, ModelProvider
from debate_tools.gateway import ToolGateway
from debate_tools.schemas import ToolPolicy, ToolRequest
from debate_tools.web_search import MockWebSearch
from debate_tracing.emitter import EventEmitter
from debate_tracing.event_store import PostgresEventStore
from pydantic import BaseModel, Field

from debate_orchestrator.claim_tracker import ClaimTracker
from debate_orchestrator.phase_engine import Phase, transition
from debate_orchestrator.types import AgentConfig, DebateInput


class Orchestrator:
    """Wires together the full debate lifecycle.

    Usage:
        orchestrator = Orchestrator(event_store, emitter)
        await orchestrator.run_debate(input)

        # With real provider:
        orchestrator = Orchestrator(event_store, emitter, provider=DeepSeekProvider())
        await orchestrator.run_debate(input)
    """

    def __init__(
        self,
        event_store: PostgresEventStore,
        emitter: EventEmitter,
        provider: ModelProvider | None = None,
    ) -> None:
        self._event_store = event_store
        self._emitter = emitter
        self._provider = provider or MockModelProvider()

    async def run_debate(self, debate_input: DebateInput) -> dict[str, Any]:
        """Execute a full mock debate run and return the final report.

        All phases use mock models and mock tools. Every transition
        and action emits events through the event store + emitter.
        """
        run_id = uuid.uuid4()

        # Setup
        harnesses = get_preset(debate_input.preset)
        if not harnesses:
            harnesses = get_preset("technical_decision")
            if not harnesses:
                return {"error": "No harnesses available"}

        provider = self._provider
        extractor = EvidenceExtractor()
        tracker = ClaimTracker()

        # Tool gateway with policy
        policy = ToolPolicy(
            agent_allowlists={h.id: h.tools_allowed for h in harnesses},
            agent_budgets={h.id: h.max_tool_calls for h in harnesses},
            run_budget=sum(h.max_tool_calls for h in harnesses),
        )
        gateway = ToolGateway(policy)
        gateway.register("web_search", MockWebSearch())

        agents = [
            AgentConfig(
                id=h.id,
                name=h.name,
                role=h.role,
                model=h.model,
                tools_allowed=h.tools_allowed,
                max_tool_calls=h.max_tool_calls,
                max_claims=h.max_claims,
            )
            for h in harnesses
        ]

        current_phase = Phase.PENDING

        # ---- Phase: run_created ----
        await self._emit(run_id, "run_created", payload={
            "topic": debate_input.topic,
            "goal": debate_input.goal,
            "preset": debate_input.preset,
            "max_rounds": debate_input.max_rounds,
        })

        # ---- Phase: agents_selected ----
        current_phase = transition(current_phase, Phase.PLANNING)
        await self._emit(run_id, "phase_transition", payload={
            "from_phase": Phase.PENDING.value,
            "to_phase": current_phase.value,
        })
        await self._emit(run_id, "agents_selected", payload={
            "agents": [a.model_dump(mode="json") for a in agents],
        })

        # ---- Phase: research planning ----
        current_phase = transition(current_phase, Phase.RESEARCHING)
        await self._emit(run_id, "phase_transition", payload={
            "from_phase": Phase.PLANNING.value,
            "to_phase": current_phase.value,
        })
        for agent in agents:
            plan = await provider.generate(
                f"Plan research for topic: {debate_input.topic}",
                _ResearchPlan,
            )
            await self._emit(run_id, "research_plan_created", actor=agent.id, payload={
                "plan": plan.model_dump(mode="json"),
            })

        # ---- Phase: evidence gathering ----
        current_phase = transition(current_phase, Phase.ARGUING)
        await self._emit(run_id, "phase_transition", payload={
            "from_phase": Phase.RESEARCHING.value,
            "to_phase": current_phase.value,
        })
        for agent in agents:
            if "web_search" in agent.tools_allowed:
                try:
                    result = await gateway.execute(
                        ToolRequest(
                            agent_id=agent.id,
                            tool_name="web_search",
                            params={"query": debate_input.topic, "limit": 3},
                        )
                    )
                    evidence_refs = await extractor.extract(
                        result.data, retrieved_by=agent.id
                    )
                    await self._emit(run_id, "evidence_gathered", actor=agent.id, payload={
                        "evidence_refs": [e.model_dump(mode="json") for e in evidence_refs],
                    })
                except Exception:
                    pass  # Budget/policy errors are non-fatal in mock mode

        # ---- Phase: opening positions ----
        current_phase = transition(current_phase, Phase.CHALLENGING)
        await self._emit(run_id, "phase_transition", payload={
            "from_phase": Phase.ARGUING.value,
            "to_phase": current_phase.value,
        })
        for agent in agents:
            position = await provider.generate(
                f"State your opening position on: {debate_input.topic}",
                _OpeningPosition,
            )
            await self._emit(run_id, "opening_position", actor=agent.id, payload={
                "position": position.model_dump(mode="json"),
            })

        # ---- Phase: cross-examination (multiple rounds) ----
        for round_num in range(debate_input.max_rounds):
            # Extract claims from opening positions (simplified: generate mock claims)
            for agent in agents:
                for i in range(min(agent.max_claims, 3)):
                    claim = tracker.add_claim(
                        f"Mock claim {i + 1} from {agent.name} about {debate_input.topic[:30]}",
                        agent.id,
                    )
                    tracker.link_evidence(claim.id, [f"E-{(i % 5) + 1:02d}"])
                    await self._emit(run_id, "claim_extracted", actor=agent.id, payload={
                        "claim": {"id": claim.id, "text": claim.text, "agent_id": claim.agent_id},
                    })

            # Challenges
            for agent in agents:
                for claim in tracker.all_claims():
                    if claim.agent_id != agent.id and claim.status != ClaimStatus.CHALLENGED:
                        tracker.challenge(
                            claim.id, agent.id,
                            f"Challenge from {agent.name}: needs stronger evidence",
                        )
                        await self._emit(run_id, "claim_challenged", actor=agent.id, payload={
                            "claim_id": claim.id,
                            "challenger": agent.id,
                        })
                        break  # One challenge per agent per round

            # Tool-backed rebuttal
            for agent in agents:
                if "web_search" in agent.tools_allowed:
                    try:
                        result = await gateway.execute(
                            ToolRequest(
                                agent_id=agent.id,
                                tool_name="web_search",
                                params={"query": f"rebuttal evidence {debate_input.topic}"},
                            )
                        )
                        evidence = await extractor.extract(result.data, retrieved_by=agent.id)
                        for ref in evidence:
                            await self._emit(run_id, "evidence_extracted", actor=agent.id, payload={
                                "evidence_ref": ref.model_dump(mode="json"),
                            })
                    except Exception:
                        pass

            # Revisions
            for agent in agents:
                revision = await provider.generate(
                    f"Revise your position on {debate_input.topic} after round {round_num + 1}",
                    _Revision,
                )
                await self._emit(run_id, "position_revised", actor=agent.id, payload={
                    "revision": revision.model_dump(mode="json"),
                })
                # Mark challenged claims as weakened
                for claim in tracker.claims_by_agent(agent.id):
                    if claim.status == ClaimStatus.CHALLENGED:
                        tracker.revoke(claim.id, f"Revised after round {round_num + 1}")

        # ---- Phase: synthesis ----
        current_phase = transition(current_phase, Phase.SYNTHESIZING)
        await self._emit(run_id, "phase_transition", payload={
            "from_phase": Phase.CHALLENGING.value,
            "to_phase": current_phase.value,
        })

        synthesis = await provider.generate(
            f"Synthesize the debate on: {debate_input.topic}",
            _Synthesis,
        )
        await self._emit(run_id, "phase_transition", payload={
            "from_phase": Phase.SYNTHESIZING.value,
            "to_phase": Phase.AUDITING.value,
        })

        # ---- Phase: evidence audit ----
        audit_data = {
            "total_claims": tracker.stats()["total"],
            "challenged": tracker.stats()["by_status"].get("challenged", 0),
            "weakened": tracker.stats()["by_status"].get("weakened", 0),
            "supported": tracker.stats()["by_status"].get("supported", 0),
        }
        await self._emit(run_id, "evidence_audit", payload={
            "audit": audit_data,
        })

        # ---- Phase: final report ----
        report = {
            "executive_synthesis": synthesis.executive_synthesis,
            "topic": debate_input.topic,
            "goal": debate_input.goal,
            "preset": debate_input.preset,
            "agents": [{"id": a.id, "name": a.name, "role": a.role} for a in agents],
            "strongest_claims": [
                {"id": c.id, "text": c.text, "agent_id": c.agent_id}
                for c in tracker.all_claims() if c.status == ClaimStatus.PROPOSED
            ],
            "challenged_claims": [
                {"id": c.id, "text": c.text, "agent_id": c.agent_id, "objections": c.objections}
                for c in tracker.all_claims() if c.status == ClaimStatus.CHALLENGED
            ],
            "agreements": synthesis.agreements,
            "disagreements": synthesis.disagreements,
            "what_changed": synthesis.what_changed,
            "final_recommendation": synthesis.final_recommendation,
            "trade_offs": synthesis.trade_offs,
            "risks": synthesis.risks,
            "open_questions": synthesis.open_questions,
            "implementation_path": synthesis.implementation_path,
            "claim_stats": tracker.stats(),
        }
        await self._emit(run_id, "final_report", payload={"report": report})

        # ---- Phase: complete ----
        current_phase = transition(Phase.AUDITING, Phase.COMPLETE)
        await self._emit(run_id, "phase_transition", payload={
            "from_phase": Phase.AUDITING.value,
            "to_phase": current_phase.value,
        })
        await self._emit(run_id, "run_completed", payload={
            "total_claims": tracker.stats()["total"],
            "rounds": debate_input.max_rounds,
            "provider_calls": provider.call_count,
            "search_calls": gateway._total_calls,
        })

        return report

    async def _emit(self, run_id: uuid.UUID, event_type: str, **kwargs: Any) -> None:
        """Emit to both event store and SSE emitter."""
        payload = kwargs.get("payload", {})
        actor = kwargs.get("actor")
        await self._event_store.append(run_id, event_type, actor=actor, payload=payload)
        await self._emitter.emit(run_id, event_type, actor=actor, payload=payload)


# ---- Response schemas for mock provider ----

class _ResearchPlan(BaseModel):
    model_config = {"extra": "forbid"}
    research_questions: list[str] = Field(default_factory=lambda: ["What is the evidence?"])
    tools_needed: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=lambda: ["Hypothesis A"])


class _OpeningPosition(BaseModel):
    model_config = {"extra": "forbid"}
    summary: str = Field(default="Opening position summary")
    key_claims: list[str] = Field(default_factory=lambda: ["Claim 1"])
    evidence_cited: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class _Revision(BaseModel):
    model_config = {"extra": "forbid"}
    what_changed: str = Field(default="Position refined after challenge")
    new_evidence_considered: list[str] = Field(default_factory=list)
    remaining_concerns: list[str] = Field(default_factory=list)


class _Synthesis(BaseModel):
    model_config = {"extra": "forbid"}
    executive_synthesis: str = Field(default="The debate produced a balanced analysis.")
    agreements: list[str] = Field(default_factory=lambda: ["Point of agreement 1"])
    disagreements: list[str] = Field(default_factory=lambda: ["Point of disagreement 1"])
    what_changed: list[str] = Field(default_factory=lambda: ["Position evolved during debate"])
    final_recommendation: str = Field(default="Adopt a bridge pattern.")
    trade_offs: list[str] = Field(default_factory=lambda: ["Trade-off: simplicity vs. flexibility"])
    risks: list[str] = Field(default_factory=lambda: ["Risk: adoption may lag"])
    open_questions: list[str] = Field(default_factory=lambda: ["Open question: timeline"])
    implementation_path: str = Field(default="Phase 1: prototype. Phase 2: pilot.")

"""Reconstruct run state from the event log."""

from __future__ import annotations

import uuid
from typing import Any

from debate_tracing.event_store import PostgresEventStore


class ReplayState:
    """Mutable state accumulator built during replay."""

    def __init__(self) -> None:
        self.status: str = "pending"
        self.current_phase: str = "pending"
        self.agents: dict[str, dict[str, Any]] = {}
        self.claims: list[dict[str, Any]] = []
        self.evidence: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []
        self.rounds: int = 0
        self.converged: bool = False
        self.final_report: dict[str, Any] | None = None
        self.event_types_seen: list[str] = []


async def reconstruct_state(
    event_store: PostgresEventStore, run_id: uuid.UUID
) -> ReplayState:
    """Replay all events for a run and return the reconstructed state.

    This is a pure derivation — the event log is the source of truth.
    No mutable state tables are read.
    """
    events = await event_store.get_events(run_id)
    state = ReplayState()

    for event in events:
        state.event_types_seen.append(event.event_type)
        _apply_event(state, event)

    return state


def _apply_event(state: ReplayState, event: Any) -> None:
    """Apply a single event to the replay state."""
    event_type = event.event_type
    payload: dict[str, Any] = event.payload or {}
    actor = event.actor

    handlers = {
        "run_created": _on_run_created,
        "agents_selected": _on_agents_selected,
        "phase_transition": _on_phase_transition,
        "research_plan_created": _on_research_plan_created,
        "evidence_gathered": _on_evidence_gathered,
        "opening_position": _on_opening_position,
        "claim_extracted": _on_claim_extracted,
        "claim_challenged": _on_claim_challenged,
        "tool_call_requested": _on_tool_call_requested,
        "tool_call_completed": _on_tool_call_completed,
        "evidence_extracted": _on_evidence_extracted,
        "position_revised": _on_position_revised,
        "convergence_check": _on_convergence_check,
        "evidence_audit": _on_evidence_audit,
        "final_report": _on_final_report,
        "run_completed": _on_run_completed,
        "run_failed": _on_run_failed,
    }

    handler = handlers.get(event_type)
    if handler:
        handler(state, payload, actor)


def _on_run_created(state: ReplayState, payload: dict, _actor: str | None) -> None:
    state.status = "pending"


def _on_agents_selected(state: ReplayState, payload: dict, _actor: str | None) -> None:
    for agent in payload.get("agents", []):
        state.agents[agent["id"]] = agent


def _on_phase_transition(state: ReplayState, payload: dict, _actor: str | None) -> None:
    state.current_phase = payload.get("to_phase", state.current_phase)
    state.status = state.current_phase


def _on_research_plan_created(state: ReplayState, payload: dict, actor: str | None) -> None:
    if actor:
        state.agents.setdefault(actor, {})["research_plan"] = payload


def _on_evidence_gathered(state: ReplayState, payload: dict, _actor: str | None) -> None:
    state.evidence.extend(payload.get("evidence_refs", []))


def _on_opening_position(state: ReplayState, payload: dict, actor: str | None) -> None:
    if actor:
        state.agents.setdefault(actor, {})["position"] = payload


def _on_claim_extracted(state: ReplayState, payload: dict, _actor: str | None) -> None:
    if "claim" in payload:
        # Update existing or append
        claim_id = payload["claim"].get("id", "")
        existing = [c for c in state.claims if c.get("id") == claim_id]
        if existing:
            existing[0].update(payload["claim"])
        else:
            state.claims.append(payload["claim"])


def _on_claim_challenged(state: ReplayState, payload: dict, _actor: str | None) -> None:
    state.tool_calls.append({"type": "challenge", **payload})


def _on_tool_call_requested(state: ReplayState, payload: dict, actor: str | None) -> None:
    state.tool_calls.append(
        {"type": "tool_request", "agent_id": actor, **payload}
    )


def _on_tool_call_completed(state: ReplayState, payload: dict, _actor: str | None) -> None:
    state.tool_calls.append({"type": "tool_result", **payload})


def _on_evidence_extracted(state: ReplayState, payload: dict, _actor: str | None) -> None:
    ref = payload.get("evidence_ref", {})
    if ref:
        state.evidence.append(ref)


def _on_position_revised(state: ReplayState, payload: dict, actor: str | None) -> None:
    if actor:
        state.agents.setdefault(actor, {})["revised_position"] = payload


def _on_convergence_check(state: ReplayState, payload: dict, _actor: str | None) -> None:
    state.converged = payload.get("converged", False)


def _on_evidence_audit(state: ReplayState, payload: dict, _actor: str | None) -> None:
    state.tool_calls.append({"type": "audit", **payload})


def _on_final_report(state: ReplayState, payload: dict, _actor: str | None) -> None:
    state.final_report = payload.get("report", {})


def _on_run_completed(state: ReplayState, _payload: dict, _actor: str | None) -> None:
    state.status = "complete"
    state.current_phase = "complete"


def _on_run_failed(state: ReplayState, payload: dict, _actor: str | None) -> None:
    state.status = "failed"
    state.current_phase = "failed"
    state.tool_calls.append({"type": "failure", "reason": payload.get("reason", "unknown")})

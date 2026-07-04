"""Deterministic phase state machine for the debate lifecycle."""

from __future__ import annotations

from debate_orchestrator.types import Phase


class InvalidPhaseTransitionError(Exception):
    """Raised when an invalid phase transition is attempted."""

    def __init__(self, current: Phase, target: Phase) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition from {current.value} to {target.value}")


# Valid transitions: current → {valid next phases}
VALID_TRANSITIONS: dict[Phase, set[Phase]] = {
    Phase.PENDING: {Phase.PLANNING, Phase.FAILED},
    Phase.PLANNING: {Phase.RESEARCHING, Phase.FAILED},
    Phase.RESEARCHING: {Phase.ARGUING, Phase.FAILED},
    Phase.ARGUING: {Phase.CHALLENGING, Phase.FAILED},
    Phase.CHALLENGING: {Phase.REVISING, Phase.SYNTHESIZING, Phase.FAILED},
    Phase.REVISING: {Phase.CHALLENGING, Phase.SYNTHESIZING, Phase.FAILED},
    Phase.SYNTHESIZING: {Phase.AUDITING, Phase.FAILED},
    Phase.AUDITING: {Phase.COMPLETE, Phase.FAILED},
    Phase.COMPLETE: set(),
    Phase.FAILED: set(),
}

# Suggested next phase for the happy path
NEXT_PHASE: dict[Phase, Phase] = {
    Phase.PENDING: Phase.PLANNING,
    Phase.PLANNING: Phase.RESEARCHING,
    Phase.RESEARCHING: Phase.ARGUING,
    Phase.ARGUING: Phase.CHALLENGING,
    Phase.CHALLENGING: Phase.REVISING,
    Phase.REVISING: Phase.SYNTHESIZING,
    Phase.SYNTHESIZING: Phase.AUDITING,
    Phase.AUDITING: Phase.COMPLETE,
}


def transition(current: Phase, target: Phase) -> Phase:
    """Validate and execute a phase transition.

    Pure function — no side effects. Returns the new phase or raises.
    """
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidPhaseTransitionError(current, target)
    return target


def next_phase(current: Phase) -> Phase:
    """Get the next happy-path phase. Raises if at a terminal."""
    nxt = NEXT_PHASE.get(current)
    if nxt is None:
        raise InvalidPhaseTransitionError(current, Phase.COMPLETE)
    return nxt


def is_terminal(phase: Phase) -> bool:
    """True if the phase is a terminal state (no valid transitions)."""
    return len(VALID_TRANSITIONS.get(phase, set())) == 0


def is_active(phase: Phase) -> bool:
    """True if the debate is still running (not terminal)."""
    return not is_terminal(phase)

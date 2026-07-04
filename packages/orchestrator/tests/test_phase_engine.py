"""Tests for the phase engine state machine."""

import pytest

from debate_orchestrator.phase_engine import (
    VALID_TRANSITIONS,
    InvalidPhaseTransitionError,
    Phase,
    is_active,
    is_terminal,
    next_phase,
    transition,
)


class TestPhaseTransitions:
    def test_valid_transition_pending_to_planning(self):
        result = transition(Phase.PENDING, Phase.PLANNING)
        assert result == Phase.PLANNING

    def test_valid_transition_planning_to_researching(self):
        result = transition(Phase.PLANNING, Phase.RESEARCHING)
        assert result == Phase.RESEARCHING

    def test_invalid_transition_raises(self):
        with pytest.raises(InvalidPhaseTransitionError) as exc:
            transition(Phase.PENDING, Phase.SYNTHESIZING)
        assert exc.value.current == Phase.PENDING
        assert exc.value.target == Phase.SYNTHESIZING

    def test_cannot_transition_from_complete(self):
        with pytest.raises(InvalidPhaseTransitionError):
            transition(Phase.COMPLETE, Phase.PLANNING)

    def test_cannot_transition_from_failed(self):
        with pytest.raises(InvalidPhaseTransitionError):
            transition(Phase.FAILED, Phase.PLANNING)

    def test_failed_from_any_active_phase(self):
        for phase in Phase:
            if is_active(phase):
                result = transition(phase, Phase.FAILED)
                assert result == Phase.FAILED

    def test_challenging_can_go_to_synthesis(self):
        result = transition(Phase.CHALLENGING, Phase.SYNTHESIZING)
        assert result == Phase.SYNTHESIZING

    def test_revising_can_loop_back_to_challenging(self):
        result = transition(Phase.REVISING, Phase.CHALLENGING)
        assert result == Phase.CHALLENGING

    def test_revising_can_go_to_synthesis(self):
        result = transition(Phase.REVISING, Phase.SYNTHESIZING)
        assert result == Phase.SYNTHESIZING


class TestNextPhase:
    def test_next_phase_happy_path(self):
        assert next_phase(Phase.PENDING) == Phase.PLANNING
        assert next_phase(Phase.PLANNING) == Phase.RESEARCHING
        assert next_phase(Phase.RESEARCHING) == Phase.ARGUING
        assert next_phase(Phase.ARGUING) == Phase.CHALLENGING

    def test_next_phase_raises_at_complete(self):
        with pytest.raises(InvalidPhaseTransitionError):
            next_phase(Phase.COMPLETE)


class TestTerminalChecks:
    def test_is_terminal_true_for_complete(self):
        assert is_terminal(Phase.COMPLETE) is True

    def test_is_terminal_true_for_failed(self):
        assert is_terminal(Phase.FAILED) is True

    def test_is_terminal_false_for_active(self):
        assert is_terminal(Phase.PENDING) is False
        assert is_terminal(Phase.ARGUING) is False

    def test_is_active_false_for_terminal(self):
        assert is_active(Phase.COMPLETE) is False
        assert is_active(Phase.FAILED) is False

    def test_is_active_true_for_running(self):
        assert is_active(Phase.PENDING) is True
        assert is_active(Phase.SYNTHESIZING) is True


class TestValidTransitions:
    def test_all_phases_have_transitions_or_are_terminal(self):
        for phase in Phase:
            assert phase in VALID_TRANSITIONS, f"{phase} missing from VALID_TRANSITIONS"

    def test_terminal_phases_have_empty_valid_targets(self):
        assert VALID_TRANSITIONS[Phase.COMPLETE] == set()
        assert VALID_TRANSITIONS[Phase.FAILED] == set()

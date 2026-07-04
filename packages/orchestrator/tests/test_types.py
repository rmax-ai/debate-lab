"""Tests for the debate types."""

from debate_orchestrator.types import DebateInput


class TestDebateInput:
    def test_valid_input(self):
        inp = DebateInput(topic="Test", goal="Decide")
        assert inp.topic == "Test"
        assert inp.goal == "Decide"
        assert inp.context == ""
        assert inp.max_rounds == 3
        assert inp.preset == "technical_decision"

    def test_topic_too_long(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DebateInput(topic="x" * 501, goal="Decide")

    def test_goal_too_long(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DebateInput(topic="Test", goal="x" * 1001)

    def test_max_rounds_out_of_range(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DebateInput(topic="Test", goal="Decide", max_rounds=0)

    def test_preset_must_be_snake_case(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DebateInput(topic="Test", goal="Decide", preset="Bad Preset")

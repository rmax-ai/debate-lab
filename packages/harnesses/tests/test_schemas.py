"""Tests for agent harness schemas."""

import pytest
from pydantic import ValidationError

from debate_harnesses.schemas import AgentHarness, HarnessRegistry


class TestAgentHarness:
    def test_valid_minimal(self):
        h = AgentHarness(id="test", name="Test", role="Test role")
        assert h.id == "test"
        assert h.model == "mock"
        assert h.tools_allowed == []
        assert h.max_claims == 10

    def test_valid_full(self):
        h = AgentHarness(
            id="advocate",
            name="Advocate",
            role="Argue for proposals",
            model="gpt-4",
            tools_allowed=["web_search", "doc_search"],
            max_tool_calls=5,
            max_claims=8,
            cost_budget=0.50,
            evidence_budget=15,
            instructions="Be rigorous.",
        )
        assert len(h.tools_allowed) == 2
        assert h.max_tool_calls == 5
        assert h.cost_budget == 0.50

    def test_invalid_id_pattern(self):
        with pytest.raises(ValidationError):
            AgentHarness(id="Bad ID!", name="X", role="X")

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            AgentHarness(id="test", name="", role="X")

    def test_empty_role_rejected(self):
        with pytest.raises(ValidationError):
            AgentHarness(id="test", name="X", role="")

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            AgentHarness(id="test", name="X", role="X", unknown_field=42)


class TestHarnessRegistry:
    def test_empty_registry(self):
        r = HarnessRegistry()
        assert len(r.harnesses) == 0
        assert r.get("nonexistent") is None

    def test_get_by_id(self):
        h = AgentHarness(id="skeptic", name="Skeptic", role="Challenge")
        r = HarnessRegistry(harnesses=[h])
        assert r.get("skeptic") is not None
        assert r.get("skeptic").name == "Skeptic"
        assert r.get("advocate") is None

    def test_get_by_role(self):
        r = HarnessRegistry(harnesses=[
            AgentHarness(id="a", name="A", role="Security analysis"),
            AgentHarness(id="b", name="B", role="Architecture review"),
            AgentHarness(id="c", name="C", role="security compliance"),
        ])
        security = r.get_by_role("security")
        assert len(security) == 2
        assert {h.id for h in security} == {"a", "c"}

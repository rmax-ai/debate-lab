"""Tests for harness presets."""

from debate_harnesses.presets import (
    get_preset,
    list_presets,
    product_strategy_preset,
    research_article_preset,
    security_review_preset,
    technical_decision_preset,
)


class TestPresets:
    def test_all_presets_have_synthesizer(self):
        """Every preset must include a synthesizer agent."""
        for name, preset_fn in [
            ("technical_decision", technical_decision_preset),
            ("research_article", research_article_preset),
            ("security_review", security_review_preset),
            ("product_strategy", product_strategy_preset),
        ]:
            agents = preset_fn()
            synthesizers = [a for a in agents if a.id == "synthesizer"]
            assert len(synthesizers) == 1, f"{name} missing synthesizer"

    def test_technical_decision_has_four_agents(self):
        agents = technical_decision_preset()
        assert len(agents) == 4
        ids = {a.id for a in agents}
        assert ids == {"advocate", "skeptic", "architect", "synthesizer"}

    def test_research_article_has_three_agents(self):
        agents = research_article_preset()
        assert len(agents) == 3
        ids = {a.id for a in agents}
        assert ids == {"proposer", "reviewer", "synthesizer"}

    def test_security_review_has_four_agents(self):
        agents = security_review_preset()
        assert len(agents) == 4
        ids = {a.id for a in agents}
        assert ids == {"proposer", "attacker", "defender", "synthesizer"}

    def test_product_strategy_has_four_agents(self):
        agents = product_strategy_preset()
        assert len(agents) == 4
        ids = {a.id for a in agents}
        assert ids == {"advocate", "skeptic", "analyst", "synthesizer"}

    def test_synthesizer_has_no_tools(self):
        """Synthesizer agents should not have tool access."""
        for agents in [
            technical_decision_preset(),
            research_article_preset(),
            security_review_preset(),
            product_strategy_preset(),
        ]:
            for agent in agents:
                if agent.id == "synthesizer":
                    assert agent.tools_allowed == [], f"{agent.id} has tools"

    def test_all_agents_have_roles(self):
        for agents in [
            technical_decision_preset(),
            research_article_preset(),
            security_review_preset(),
            product_strategy_preset(),
        ]:
            for agent in agents:
                assert len(agent.role) > 20, f"{agent.id} role too short"

    def test_get_preset(self):
        agents = get_preset("technical_decision")
        assert agents is not None
        assert len(agents) == 4

    def test_get_preset_nonexistent(self):
        assert get_preset("nonexistent") is None

    def test_list_presets(self):
        names = list_presets()
        assert "technical_decision" in names
        assert "security_review" in names
        assert len(names) == 4

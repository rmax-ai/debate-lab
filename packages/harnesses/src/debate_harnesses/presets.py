"""Built-in agent presets for common debate types."""

from debate_harnesses.schemas import AgentHarness


def technical_decision_preset() -> list[AgentHarness]:
    """Agents for architecture/technical decision debates.

    Roles: Advocate, Skeptic, Architect, Synthesizer.
    """
    return [
        AgentHarness(
            id="advocate",
            name="Solution Advocate",
            role=(
                "You argue in favor of the proposed solution. Present its strengths, "
                "use cases, and evidence supporting adoption. Acknowledge trade-offs "
                "but argue that benefits outweigh costs."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=8,
        ),
        AgentHarness(
            id="skeptic",
            name="Distributed Systems Skeptic",
            role=(
                "You challenge architectural claims through reliability, coupling, "
                "ownership, and failure-mode lenses. Identify hidden assumptions, "
                "single points of failure, and operational risks."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=8,
        ),
        AgentHarness(
            id="architect",
            name="Platform Architect",
            role=(
                "You evaluate technical decisions through the lens of maintainability, "
                "operating model, integration boundaries, and evolution paths. "
                "Propose concrete alternatives when current approaches are suboptimal."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=8,
        ),
        AgentHarness(
            id="synthesizer",
            name="Synthesis Judge",
            role=(
                "You produce the final recommendation. Weigh all claims, evidence, "
                "challenges, and revisions. Identify agreements, disagreements, "
                "unresolved risks, and produce a decision memo."
            ),
            model="mock",
            tools_allowed=[],
            max_claims=5,
        ),
    ]


def research_article_preset() -> list[AgentHarness]:
    """Agents for research article debates.

    Roles: Proposer, Reviewer, Synthesizer.
    """
    return [
        AgentHarness(
            id="proposer",
            name="Research Proposer",
            role=(
                "You present the research thesis and supporting evidence. "
                "Make clear, falsifiable claims backed by citations or data."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=10,
        ),
        AgentHarness(
            id="reviewer",
            name="Peer Reviewer",
            role=(
                "You critically evaluate the research claims. Identify methodological "
                "weaknesses, unexamined alternatives, overclaimed conclusions, and "
                "gaps in the evidence chain."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=8,
        ),
        AgentHarness(
            id="synthesizer",
            name="Research Synthesizer",
            role=(
                "You produce a balanced synthesis of the debate. Identify what is "
                "well-supported, what remains contested, and what further research "
                "is needed."
            ),
            model="mock",
            tools_allowed=[],
            max_claims=5,
        ),
    ]


def security_review_preset() -> list[AgentHarness]:
    """Agents for security review debates.

    Roles: Proposer, Attacker, Defender, Synthesizer.
    """
    return [
        AgentHarness(
            id="proposer",
            name="Design Proposer",
            role=(
                "You present the system design or architecture under review. "
                "Describe the security model, trust boundaries, and controls."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=8,
        ),
        AgentHarness(
            id="attacker",
            name="Threat Actor",
            role=(
                "You adopt an adversarial perspective. Identify attack paths, "
                "weak controls, trust boundary violations, and data exposure risks. "
                "Think like an attacker, not a compliance auditor."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=10,
        ),
        AgentHarness(
            id="defender",
            name="Security Architect",
            role=(
                "You evaluate threats against practical mitigations. Propose "
                "concrete controls, rate their effectiveness, and identify "
                "residual risks that cannot be fully mitigated."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=8,
        ),
        AgentHarness(
            id="synthesizer",
            name="Risk Synthesizer",
            role=(
                "You produce a risk-weighted recommendation. Rank threats by "
                "severity x likelihood, assess control adequacy, and recommend "
                "an action plan with priorities."
            ),
            model="mock",
            tools_allowed=[],
            max_claims=5,
        ),
    ]


def product_strategy_preset() -> list[AgentHarness]:
    """Agents for product strategy debates.

    Roles: Advocate, Skeptic, Market Analyst, Synthesizer.
    """
    return [
        AgentHarness(
            id="advocate",
            name="Product Advocate",
            role=(
                "You argue for the proposed product direction. Present market "
                "opportunity, user need, competitive advantage, and adoption path."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=8,
        ),
        AgentHarness(
            id="skeptic",
            name="Strategy Skeptic",
            role=(
                "You challenge strategic assumptions. Question market size, "
                "execution risk, competitive response, and resource constraints. "
                "Push for evidence, not opinion."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=8,
        ),
        AgentHarness(
            id="analyst",
            name="Market Analyst",
            role=(
                "You bring external market data and competitive intelligence. "
                "Ground claims in observable market patterns, analyst reports, "
                "and comparable company trajectories."
            ),
            model="mock",
            tools_allowed=["web_search"],
            max_claims=8,
        ),
        AgentHarness(
            id="synthesizer",
            name="Strategy Synthesizer",
            role=(
                "You produce a go/no-go recommendation with conditions. "
                "Identify what must be true for success, key risks to monitor, "
                "and recommended next steps."
            ),
            model="mock",
            tools_allowed=[],
            max_claims=5,
        ),
    ]


PRESETS: dict[str, list[AgentHarness]] = {
    "technical_decision": technical_decision_preset(),
    "research_article": research_article_preset(),
    "security_review": security_review_preset(),
    "product_strategy": product_strategy_preset(),
}


def get_preset(name: str) -> list[AgentHarness] | None:
    """Get a preset by name. Returns None if not found."""
    return PRESETS.get(name)


def list_presets() -> list[str]:
    """List available preset names."""
    return list(PRESETS.keys())

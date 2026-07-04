"""Pydantic schemas for agent harnesses and the harness registry."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentHarness(BaseModel):
    """Definition of a single agent harness.

    A harness wraps a model with a role, tool policy, output schema, and budget.
    Agents never call tools or models directly — they go through the harness.
    """

    model_config = {"extra": "forbid"}

    id: str = Field(..., pattern=r"^[a-z_]+$", description="Machine-readable ID")
    name: str = Field(..., min_length=1, description="Human-readable name")
    role: str = Field(..., min_length=1, description="Role description for the LLM prompt")
    model: str = Field(default="mock", description="Model identifier")
    tools_allowed: list[str] = Field(
        default_factory=list,
        description="Tool names this agent may use",
    )
    max_tool_calls: int = Field(default=8, ge=0, description="Max tool calls per agent")
    max_claims: int = Field(default=10, ge=1, description="Max claims per agent")
    cost_budget: float = Field(default=0.0, ge=0.0, description="Max USD cost")
    evidence_budget: int = Field(default=20, ge=0, description="Max evidence refs")
    instructions: str = Field(default="", description="Additional system instructions")


class HarnessRegistry(BaseModel):
    """Collection of agent harness definitions, typically loaded from config."""

    model_config = {"extra": "forbid"}

    harnesses: list[AgentHarness] = Field(default_factory=list)

    def get(self, agent_id: str) -> AgentHarness | None:
        """Find a harness by ID."""
        for h in self.harnesses:
            if h.id == agent_id:
                return h
        return None

    def get_by_role(self, role_pattern: str) -> list[AgentHarness]:
        """Find harnesses whose role contains the given pattern."""
        pattern = role_pattern.lower()
        return [h for h in self.harnesses if pattern in h.role.lower()]

    def select_for_preset(self, preset: str) -> list[AgentHarness]:
        """Select agents for a given preset.

        The preset is a tag applied to matching harness IDs.
        This is a simple string-match filter — real selection logic
        lives in the orchestrator.
        """
        return [h for h in self.harnesses if f":{preset}" in h.id or h.id.startswith(preset)]

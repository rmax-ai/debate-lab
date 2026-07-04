"""Pydantic schemas for the tool gateway."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    """Request from an agent to use a tool."""

    model_config = {"extra": "forbid"}

    agent_id: str = Field(..., pattern=r"^[a-z_]+$")
    tool_name: str = Field(..., min_length=1)
    params: dict = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of a tool execution."""

    model_config = {"extra": "forbid"}

    tool_name: str
    agent_id: str
    data: dict = Field(default_factory=dict)
    evidence_ref_ids: list[str] = Field(default_factory=list)
    summary: str = Field(default="")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolPolicy(BaseModel):
    """Policy governing tool access for a debate run."""

    model_config = {"extra": "forbid"}

    agent_allowlists: dict[str, list[str]] = Field(
        default_factory=dict,
        description="agent_id -> list of allowed tool names",
    )
    run_budget: int = Field(default=50, ge=0, description="Max tool calls per run")
    agent_budgets: dict[str, int] = Field(
        default_factory=dict,
        description="agent_id -> max tool calls for that agent",
    )
    allowed_tools: set[str] = Field(
        default_factory=set,
        description="Global set of available tool names",
    )

    def is_allowed(self, agent_id: str, tool_name: str) -> bool:
        """Check if an agent is allowed to use a tool."""
        if tool_name not in self.allowed_tools:
            return False
        allowed = self.agent_allowlists.get(agent_id, [])
        return tool_name in allowed

    def get_agent_budget(self, agent_id: str) -> int:
        """Get the max tool calls allowed for an agent."""
        return self.agent_budgets.get(agent_id, self.run_budget)

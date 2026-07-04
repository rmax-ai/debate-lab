"""Core types for the debate orchestrator."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Phase(StrEnum):
    """Debate run phases in order."""

    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    ARGUING = "arguing"
    CHALLENGING = "challenging"
    REVISING = "revising"
    SYNTHESIZING = "synthesizing"
    AUDITING = "auditing"
    COMPLETE = "complete"
    FAILED = "failed"


class DebateInput(BaseModel):
    """User input to create a new debate run."""

    model_config = {"extra": "forbid"}

    topic: str = Field(..., min_length=1, max_length=500)
    context: str = Field(default="", max_length=5000)
    goal: str = Field(..., min_length=1, max_length=1000)
    constraints: str = Field(default="", max_length=2000)
    max_rounds: int = Field(default=3, ge=1, le=5)
    preset: str = Field(default="technical_decision", pattern=r"^[a-z_]+$")


class AgentConfig(BaseModel):
    """Selected agent harness for a run."""

    model_config = {"extra": "forbid"}

    id: str = Field(..., pattern=r"^[a-z_]+$")
    name: str
    role: str
    model: str
    tools_allowed: list[str] = Field(default_factory=list)
    max_tool_calls: int = 8
    max_claims: int = 10


class DebateRunState(BaseModel):
    """Current state of a debate run, reconstructed from events."""

    model_config = {"extra": "forbid"}

    run_id: str
    topic: str
    status: Phase = Phase.PENDING
    current_phase: Phase = Phase.PENDING
    selected_agents: list[AgentConfig] = Field(default_factory=list)
    rounds_completed: int = 0
    max_rounds: int = 3
    converged: bool = False

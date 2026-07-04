"""Tests for the tool gateway."""

import pytest

from debate_tools.gateway import (
    AgentBudgetExceededError,
    RunBudgetExceededError,
    ToolGateway,
    ToolNotAllowedError,
    UnknownToolError,
)
from debate_tools.schemas import ToolPolicy, ToolRequest


class FakeSearchTool:
    """Fake tool implementation for testing."""

    def __init__(self, response: dict | None = None):
        self.response = response or {"results": [], "summary": "no results"}

    async def execute(self, params: dict) -> dict:
        return self.response


class TestToolPolicy:
    def test_is_allowed(self):
        policy = ToolPolicy(
            agent_allowlists={"advocate": ["web_search"]},
            allowed_tools={"web_search"},
        )
        assert policy.is_allowed("advocate", "web_search") is True
        assert policy.is_allowed("skeptic", "web_search") is False
        assert policy.is_allowed("advocate", "nonexistent") is False

    def test_agent_budget(self):
        policy = ToolPolicy(
            agent_budgets={"advocate": 5},
            run_budget=20,
        )
        assert policy.get_agent_budget("advocate") == 5
        assert policy.get_agent_budget("unknown") == 20  # falls back to run budget


class TestToolGateway:
    @pytest.fixture
    def gateway(self):
        policy = ToolPolicy(
            agent_allowlists={"agent_a": ["search"]},
            agent_budgets={"agent_a": 3},
            run_budget=10,
        )
        gw = ToolGateway(policy)
        gw.register("search", FakeSearchTool())
        return gw

    async def test_execute_allowed(self, gateway):
        request = ToolRequest(agent_id="agent_a", tool_name="search", params={"q": "test"})
        result = await gateway.execute(request)
        assert result.tool_name == "search"
        assert result.agent_id == "agent_a"

    async def test_unknown_tool_raises(self, gateway):
        request = ToolRequest(agent_id="agent_a", tool_name="nonexistent")
        with pytest.raises(UnknownToolError):
            await gateway.execute(request)

    async def test_not_allowed_raises(self, gateway):
        request = ToolRequest(agent_id="agent_b", tool_name="search")
        with pytest.raises(ToolNotAllowedError):
            await gateway.execute(request)

    async def test_agent_budget_exceeded(self, gateway):
        req = ToolRequest(agent_id="agent_a", tool_name="search")
        for _ in range(3):
            await gateway.execute(req)
        with pytest.raises(AgentBudgetExceededError):
            await gateway.execute(req)

    async def test_run_budget_exceeded(self, gateway):
        policy = ToolPolicy(
            agent_allowlists={"a": ["search"], "b": ["search"]},
            run_budget=2,
        )
        gw = ToolGateway(policy)
        gw.register("search", FakeSearchTool())

        await gw.execute(ToolRequest(agent_id="a", tool_name="search"))
        await gw.execute(ToolRequest(agent_id="b", tool_name="search"))
        with pytest.raises(RunBudgetExceededError):
            await gw.execute(ToolRequest(agent_id="a", tool_name="search"))

    async def test_registered_tools(self, gateway):
        assert "search" in gateway.registered_tools()

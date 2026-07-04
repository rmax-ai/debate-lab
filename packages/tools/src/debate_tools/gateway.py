"""Tool gateway — mediates all agent tool access with policy enforcement."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from debate_tools.schemas import ToolPolicy, ToolRequest, ToolResult


class ToolPolicyError(Exception):
    """Raised when a tool policy violation occurs."""


class ToolNotAllowedError(ToolPolicyError):
    """Agent is not allowed to use this tool."""

    def __init__(self, agent_id: str, tool_name: str) -> None:
        super().__init__(f"Agent '{agent_id}' is not allowed to use '{tool_name}'")


class AgentBudgetExceededError(ToolPolicyError):
    """Agent has exceeded its tool call budget."""

    def __init__(self, agent_id: str, used: int, budget: int) -> None:
        super().__init__(
            f"Agent '{agent_id}' has used {used}/{budget} tool calls"
        )


class RunBudgetExceededError(ToolPolicyError):
    """Run has exceeded its global tool call budget."""

    def __init__(self, used: int, budget: int) -> None:
        super().__init__(f"Run budget exceeded: {used}/{budget} tool calls")


class UnknownToolError(ToolPolicyError):
    """Requested tool is not registered."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Unknown tool: '{tool_name}'")


@runtime_checkable
class ToolImplementation(Protocol):
    """Protocol for tool implementations."""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool and return raw results."""
        ...


class ToolGateway:
    """Mediates all agent tool access with policy enforcement.

    Flow:
        Agent request → policy check → execute tool → produce result → return
    """

    def __init__(self, policy: ToolPolicy) -> None:
        self._policy = policy
        self._tools: dict[str, ToolImplementation] = {}
        self._agent_call_counts: dict[str, int] = {}
        self._total_calls: int = 0

    def register(self, name: str, tool: ToolImplementation) -> None:
        """Register a tool implementation."""
        self._tools[name] = tool
        self._policy.allowed_tools.add(name)

    def registered_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    async def execute(self, request: ToolRequest) -> ToolResult:
        """Execute a tool call through the gateway.

        Raises:
            UnknownToolError: tool not registered
            ToolNotAllowedError: agent not allowed
            AgentBudgetExceededError: agent over budget
            RunBudgetExceededError: run over budget
        """
        # 1. Validate tool exists
        if request.tool_name not in self._tools:
            raise UnknownToolError(request.tool_name)

        # 2. Policy check: is agent allowed?
        if not self._policy.is_allowed(request.agent_id, request.tool_name):
            raise ToolNotAllowedError(request.agent_id, request.tool_name)

        # 3. Policy check: agent budget
        agent_used = self._agent_call_counts.get(request.agent_id, 0)
        agent_budget = self._policy.get_agent_budget(request.agent_id)
        if agent_used >= agent_budget:
            raise AgentBudgetExceededError(
                request.agent_id, agent_used, agent_budget
            )

        # 4. Policy check: run budget
        if self._total_calls >= self._policy.run_budget:
            raise RunBudgetExceededError(self._total_calls, self._policy.run_budget)

        # 5. Execute tool
        tool = self._tools[request.tool_name]
        raw_result = await tool.execute(request.params)

        # 6. Track usage
        self._agent_call_counts[request.agent_id] = agent_used + 1
        self._total_calls += 1

        return ToolResult(
            tool_name=request.tool_name,
            agent_id=request.agent_id,
            data=raw_result,
            summary=raw_result.get("summary", f"Tool {request.tool_name} completed"),
        )

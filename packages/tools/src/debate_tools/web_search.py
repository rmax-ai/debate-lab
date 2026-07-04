"""Mock web search implementation."""

from __future__ import annotations

from typing import Any

MOCK_SEARCH_RESULTS: list[dict[str, Any]] = [
    {
        "title": "Event-Driven Architecture vs. Chat-Based Workflows",
        "url": "https://example.com/eda-vs-chat",
        "snippet": (
            "Event-driven architectures provide explicit delivery semantics, "
            "replay capability, and clear ownership boundaries. Chat-based "
            "workflows excel at human-in-the-loop approvals but lack durability "
            "guarantees for business-critical operations."
        ),
    },
    {
        "title": "Operational Reliability Patterns",
        "url": "https://example.com/ops-reliability",
        "snippet": (
            "Systems of record require at-least-once delivery, idempotent "
            "processing, and audit trails. Notification surfaces like Slack "
            "are best used as presentation layers, not authoritative sources."
        ),
    },
    {
        "title": "Enterprise Workflow Adoption Study",
        "url": "https://example.com/adoption-study",
        "snippet": (
            "Teams already operating in Slack show 40% faster adoption of "
            "workflow tools when Slack remains the interaction surface. "
            "Migration from Slack-native workflows to event-bus patterns "
            "requires explicit ownership assignment and schema governance."
        ),
    },
    {
        "title": "Security Considerations for Operational Signals",
        "url": "https://example.com/security-signals",
        "snippet": (
            "Operational signals routed through chat platforms inherit the "
            "platform's permission model. Event buses allow fine-grained "
            "authorization per event type, consumer, and producer."
        ),
    },
    {
        "title": "Cost Analysis: Event Bus Infrastructure",
        "url": "https://example.com/cost-event-bus",
        "snippet": (
            "Managed event bus services cost $0.50-2.00 per million events. "
            "Self-hosted alternatives (Kafka, NATS) have higher operational "
            "cost but lower per-event cost at scale."
        ),
    },
]


class MockWebSearch:
    """Deterministic mock web search for testing."""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self._results = results or MOCK_SEARCH_RESULTS
        self.call_count = 0
        self.call_history: list[dict[str, Any]] = []

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a mock search and return results."""
        self.call_count += 1
        query = params.get("query", "")
        limit = min(params.get("limit", 5), len(self._results))

        self.call_history.append({
            "call": self.call_count,
            "query": query,
            "limit": limit,
        })

        return {
            "query": query,
            "results": self._results[:limit],
            "total_results": len(self._results),
            "summary": f"Found {limit} results for '{query[:50]}...'",
        }

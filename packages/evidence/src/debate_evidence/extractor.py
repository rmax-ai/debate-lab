"""Evidence extractor — produces EvidenceRef objects from tool results."""

from __future__ import annotations

from typing import Any

from debate_evidence.schemas import EvidenceRef


class EvidenceExtractor:
    """Extracts EvidenceRef objects from tool call results.

    Each tool result is processed to produce structured evidence references
    that can be linked to claims.
    """

    def __init__(self, ref_counter: int = 0) -> None:
        self._counter = ref_counter

    async def extract(
        self, tool_result: dict[str, Any], *, retrieved_by: str
    ) -> list[EvidenceRef]:
        """Extract evidence refs from a tool result dict.

        Handles web_search results (list of {title, url, snippet}) and
        generic dict results.
        """
        refs: list[EvidenceRef] = []

        source_type = tool_result.get("source_type", "web_search")
        results = tool_result.get("results", [])

        if isinstance(results, list):
            for item in results:
                if not isinstance(item, dict):
                    continue
                self._counter += 1
                refs.append(
                    EvidenceRef(
                        id=f"E-{self._counter:02d}",
                        source_type=source_type,
                        url=item.get("url"),
                        title=item.get("title", f"Result {self._counter}"),
                        quote_or_excerpt=item.get("snippet", item.get("quote", "")),
                        extracted_facts=item.get("extracted_facts", []),
                        reliability_score=item.get("reliability_score", 0.5),
                        retrieved_by=retrieved_by,
                    )
                )
        elif isinstance(results, dict):
            self._counter += 1
            refs.append(
                EvidenceRef(
                    id=f"E-{self._counter:02d}",
                    source_type=source_type,
                    title=results.get("title", f"Result {self._counter}"),
                    quote_or_excerpt=str(results),
                    retrieved_by=retrieved_by,
                )
            )

        return refs

    def reset_counter(self) -> None:
        """Reset the evidence reference counter."""
        self._counter = 0

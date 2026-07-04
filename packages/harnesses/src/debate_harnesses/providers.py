"""Model provider protocol and mock implementation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class ModelProvider(Protocol):
    """Protocol for model providers.

    All providers accept a prompt string and a Pydantic response schema,
    and return a validated instance of that schema.
    """

    async def generate(self, prompt: str, response_schema: type[BaseModel]) -> BaseModel:
        """Generate a structured response matching the given schema."""
        ...


class MockModelProvider:
    """Deterministic mock provider for testing.

    Returns pre-configured responses based on the response_schema type.
    Useful for testing the debate lifecycle without real LLM calls.
    """

    def __init__(self, responses: dict[str, dict[str, Any]] | None = None) -> None:
        """Initialize with optional pre-configured responses.

        Args:
            responses: Dict mapping schema class name to a dict of field values.
                       If not provided, sensible defaults are generated.
        """
        self._responses = responses or {}
        self.call_count = 0
        self.call_history: list[dict[str, Any]] = []

    async def generate(self, prompt: str, response_schema: type[BaseModel]) -> BaseModel:
        """Return a deterministic response matching the schema.

        If a pre-configured response exists for this schema, use it.
        Otherwise, generate sensible defaults from the schema's field types.
        """
        self.call_count += 1
        schema_name = response_schema.__name__

        self.call_history.append({
            "call": self.call_count,
            "schema": schema_name,
            "prompt_preview": prompt[:100],
        })

        # Use pre-configured response if available
        if schema_name in self._responses:
            return response_schema(**self._responses[schema_name])

        # Generate sensible defaults from schema fields
        defaults = self._generate_defaults(response_schema)
        return response_schema(**defaults)

    def _generate_defaults(self, schema: type[BaseModel]) -> dict[str, Any]:
        """Generate sensible default values for a Pydantic schema."""
        result: dict[str, Any] = {}
        for field_name, field_info in schema.model_fields.items():
            annotation = field_info.annotation
            if annotation is str:
                result[field_name] = f"mock_{field_name}"
            elif annotation is int:
                result[field_name] = 1
            elif annotation is float:
                result[field_name] = 0.5
            elif annotation is bool:
                result[field_name] = False
            elif hasattr(annotation, "__origin__") and annotation.__origin__ is list:
                result[field_name] = []
            elif hasattr(annotation, "__origin__") and annotation.__origin__ is dict:
                result[field_name] = {}
            elif field_info.default is not None and field_info.default is not ...:
                result[field_name] = field_info.default
        return result

"""Real LLM provider adapters for DebateLab.

Implements the ModelProvider protocol for:
- OpenAI (native structured output via json_schema)
- DeepSeek (OpenAI-compatible, JSON mode + prompt injection)
- Gemini (Google GenAI, native structured output)

Default cheap models:
- openai: gpt-4o-mini (~$0.15/M input, ~$0.60/M output)
- deepseek: deepseek-chat (~$0.27/M input, ~$1.10/M output)
- gemini: gemini-2.0-flash (free tier, rate-limited)

API keys from env vars: OPENAI_API_KEY, DEEPSEEK_API_KEY, GEMINI_API_KEY
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from pydantic import BaseModel

from debate_harnesses.providers import ModelProvider

logger = logging.getLogger(__name__)


def _describe_schema(schema: type[BaseModel]) -> str:
    """Build a human-readable description of a Pydantic schema for the prompt.

    Produces compact output like:
        {
          "summary": "<string>",
          "confidence": <float 0.0-1.0>,
          "key_points": ["<string>", ...]
        }
    """
    lines = ["{"]
    for field_name, field_info in schema.model_fields.items():
        annotation = field_info.annotation
        type_desc = _field_type_desc(annotation)
        desc = field_info.description or ""

        # Build constraints
        constraints = ""
        for meta in field_info.metadata:
            if hasattr(meta, "ge") and hasattr(meta, "le"):
                constraints = f" {meta.ge}-{meta.le}"
            elif hasattr(meta, "min_length") and hasattr(meta, "max_length"):
                constraints = f" min_len={meta.min_length} max_len={meta.max_length}"

        comment = f"  // {desc}" if desc else ""
        lines.append(f'  "{field_name}": {type_desc}{constraints},{comment}')
    lines.append("}")
    return "\n".join(lines)


def _field_type_desc(annotation: Any) -> str:
    """Convert a type annotation to a readable string."""
    import types

    if annotation is str:
        return "<string>"
    if annotation is int:
        return "<integer>"
    if annotation is float:
        return "<float>"
    if annotation is bool:
        return "<boolean>"
    if annotation is list or (hasattr(annotation, "__origin__") and annotation.__origin__ is list):
        inner = "string"
        if hasattr(annotation, "__args__") and annotation.__args__:
            inner = _field_type_desc(annotation.__args__[0])
        return f"[<{inner}>, ...]"
    if annotation is dict:
        return "<object>"
    if isinstance(annotation, types.UnionType):
        args = [a for a in annotation.__args__ if a is not types.NoneType]
        if len(args) == 1:
            return f"{_field_type_desc(args[0])} | null"
        return " | ".join(_field_type_desc(a) for a in args)
    return "<any>"


class DeepSeekProvider:
    """DeepSeek API provider via OpenAI-compatible endpoint.

    Uses the openai package pointed at api.deepseek.com.
    Supports structured output via response_format.
    """

    BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        model: str = "deepseek-chat",
        temperature: float = 0.0,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self._call_count = 0

        if not self._api_key:
            logger.warning(
                "DEEPSEEK_API_KEY not set — DeepSeekProvider will fail on generate()"
            )

    @property
    def call_count(self) -> int:
        return self._call_count

    async def generate(self, prompt: str, response_schema: type[BaseModel]) -> BaseModel:
        """Generate a structured response via DeepSeek API.

        DeepSeek does not support native structured output (json_schema type).
        We use basic JSON mode and embed the schema in the system prompt.
        """
        from openai import AsyncOpenAI

        self._call_count += 1

        client = AsyncOpenAI(api_key=self._api_key, base_url=self.BASE_URL)

        # Build schema description for the prompt
        schema_desc = _describe_schema(response_schema)

        response = await client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a structured debate agent. "
                        "Respond ONLY with a valid JSON object. "
                        "No markdown fences, no commentary — pure JSON.\n\n"
                        f"Required JSON schema:\n{schema_desc}"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        if raw is None:
            raise RuntimeError("DeepSeek returned empty response")

        data = json.loads(raw)
        return response_schema.model_validate(data)


class GeminiProvider:
    """Google Gemini provider via google-genai SDK.

    Supports structured output via response_schema parameter.
    Uses gemini-2.0-flash by default (free tier).
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.0,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._call_count = 0

        if not self._api_key:
            logger.warning(
                "GEMINI_API_KEY not set — GeminiProvider will fail on generate()"
            )

    @property
    def call_count(self) -> int:
        return self._call_count

    async def generate(self, prompt: str, response_schema: type[BaseModel]) -> BaseModel:
        """Generate a structured response via Gemini API."""
        from google import genai

        self._call_count += 1

        client = genai.Client(api_key=self._api_key)

        # Gemini uses snake_case param names
        response = await client.aio.models.generate_content(
            model=self.model,
            contents=(
                "You are a structured debate agent. "
                "Respond ONLY with valid JSON matching the requested schema."
                f"\n\nPrompt: {prompt}"
            ),
            config={
                "temperature": self.temperature,
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            },
        )

        raw = response.text
        if raw is None:
            raise RuntimeError("Gemini returned empty response")

        data = json.loads(raw)
        return response_schema.model_validate(data)


class OpenAIProvider:
    """OpenAI provider with native structured output (json_schema).

    Uses the openai package with default base URL.
    Native structured output means strict schema enforcement —
    the model CANNOT produce output that doesn't match the schema.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._call_count = 0

        if not self._api_key:
            logger.warning(
                "OPENAI_API_KEY not set — OpenAIProvider will fail on generate()"
            )

    @property
    def call_count(self) -> int:
        return self._call_count

    async def generate(self, prompt: str, response_schema: type[BaseModel]) -> BaseModel:
        """Generate a structured response via OpenAI with native schema enforcement."""
        from openai import AsyncOpenAI

        self._call_count += 1

        client = AsyncOpenAI(api_key=self._api_key)

        schema_json = response_schema.model_json_schema()

        response = await client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a structured debate agent. "
                        "Respond with valid JSON matching the schema exactly."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "strict": True,
                    "schema": schema_json,
                },
            },
        )

        raw = response.choices[0].message.content
        if raw is None:
            raise RuntimeError("OpenAI returned empty response")

        data = json.loads(raw)
        return response_schema.model_validate(data)


class FallbackProvider:
    """Provider that tries real providers in order, falling back to mock.

    Usage:
        provider = FallbackProvider([
            DeepSeekProvider(),
            GeminiProvider(),
        ], mock=MockModelProvider())
    """

    def __init__(
        self,
        providers: list[ModelProvider],
        mock: ModelProvider | None = None,
    ) -> None:
        self._providers = providers
        self._mock = mock
        self._call_count = 0
        self._provider_stats: dict[str, int] = {}

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def provider_stats(self) -> dict[str, int]:
        return dict(self._provider_stats)

    async def generate(self, prompt: str, response_schema: type[BaseModel]) -> BaseModel:
        """Try each provider in order; fall back to mock if all fail."""
        self._call_count += 1

        for provider in self._providers:
            name = type(provider).__name__
            try:
                result = await provider.generate(prompt, response_schema)
                self._provider_stats[name] = self._provider_stats.get(name, 0) + 1
                return result
            except Exception as exc:
                logger.warning(
                    "Provider %s failed: %s — trying next", name, exc
                )
                continue

        if self._mock is not None:
            logger.warning("All real providers failed — falling back to mock")
            self._provider_stats["mock"] = self._provider_stats.get("mock", 0) + 1
            return await self._mock.generate(prompt, response_schema)

        raise RuntimeError("All providers failed and no mock fallback configured")

"""Tests for the mock model provider."""

from pydantic import BaseModel

from debate_harnesses.providers import MockModelProvider


class SimpleResponse(BaseModel):
    text: str
    confidence: float


class ListResponse(BaseModel):
    items: list[str]
    count: int


class TestMockModelProvider:
    async def test_generate_uses_defaults(self):
        provider = MockModelProvider()
        result = await provider.generate("some prompt", SimpleResponse)
        assert isinstance(result, SimpleResponse)
        assert result.text == "mock_text"
        assert result.confidence == 0.5
        assert provider.call_count == 1
        assert len(provider.call_history) == 1

    async def test_generate_with_preconfigured(self):
        provider = MockModelProvider(
            responses={"SimpleResponse": {"text": "custom", "confidence": 0.9}}
        )
        result = await provider.generate("prompt", SimpleResponse)
        assert result.text == "custom"
        assert result.confidence == 0.9

    async def test_generate_list_defaults(self):
        provider = MockModelProvider()
        result = await provider.generate("prompt", ListResponse)
        assert isinstance(result, ListResponse)
        assert result.items == []
        assert result.count == 1

    async def test_call_count_increments(self):
        provider = MockModelProvider()
        await provider.generate("p1", SimpleResponse)
        await provider.generate("p2", SimpleResponse)
        await provider.generate("p3", ListResponse)
        assert provider.call_count == 3
        assert provider.call_history[0]["schema"] == "SimpleResponse"
        assert provider.call_history[2]["schema"] == "ListResponse"

    async def test_call_history_records_prompt(self):
        provider = MockModelProvider()
        await provider.generate("What is the best approach?", SimpleResponse)
        assert "What is the best" in provider.call_history[0]["prompt_preview"]

    async def test_provider_satisfies_protocol(self):
        from debate_harnesses.providers import ModelProvider

        provider = MockModelProvider()
        assert isinstance(provider, ModelProvider)

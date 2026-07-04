"""Agent harness definitions, providers, and presets for DebateLab.

A harness is: model + role prompt + tool policy + output schema + budget.
"""

from debate_harnesses.providers import MockModelProvider, ModelProvider
from debate_harnesses.real_providers import (
    DeepSeekProvider,
    FallbackProvider,
    GeminiProvider,
    OpenAIProvider,
)
from debate_harnesses.registry import HarnessLoader
from debate_harnesses.schemas import AgentHarness, HarnessRegistry

__all__ = [
    "AgentHarness",
    "DeepSeekProvider",
    "FallbackProvider",
    "GeminiProvider",
    "HarnessLoader",
    "HarnessRegistry",
    "MockModelProvider",
    "ModelProvider",
    "OpenAIProvider",
]

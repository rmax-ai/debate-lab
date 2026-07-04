"""Configuration loader for DebateLab.

Loads debate.toml from the project root and builds the appropriate
model provider based on configuration and available API keys.
"""

from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from debate_harnesses.providers import MockModelProvider, ModelProvider
from debate_harnesses.real_providers import (
    DeepSeekProvider,
    FallbackProvider,
    GeminiProvider,
)

logger = logging.getLogger(__name__)


def _find_config() -> Path | None:
    """Find debate.toml by searching upward from cwd."""
    env_path = os.environ.get("DEBATE_CONFIG")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / "debate.toml"
        if candidate.exists():
            return candidate
    return None


@dataclass
class DebateConfig:
    """Parsed DebateLab configuration."""

    provider: ModelProvider
    provider_name: str
    orchestrator: dict = field(default_factory=dict)
    api: dict = field(default_factory=dict)


def load_config() -> DebateConfig:
    """Load debate.toml and build the configured model provider.

    Resolution order:
    1. Parse debate.toml → get provider.default
    2. If provider is "fallback", try real providers in configured order
    3. If API key is missing for a provider, skip it
    4. If all real providers are unavailable, use MockModelProvider

    Returns:
        DebateConfig with the resolved provider and parsed settings.
    """
    config_path = _find_config()
    raw: dict = {}

    if config_path is not None:
        raw = tomllib.loads(config_path.read_text())
        logger.info("Loaded config from %s", config_path)
    else:
        logger.warning("No debate.toml found — using mock provider")

    provider_cfg = raw.get("provider", {})
    provider_name = provider_cfg.get("default", "mock")

    provider = _build_provider(provider_name, provider_cfg)
    orchestrator_cfg = raw.get("orchestrator", {})
    api_cfg = raw.get("api", {})

    return DebateConfig(
        provider=provider,
        provider_name=provider._actual_name if hasattr(provider, "_actual_name") else provider_name,
        orchestrator=orchestrator_cfg,
        api=api_cfg,
    )


def _build_provider(name: str, cfg: dict) -> ModelProvider:
    """Build a ModelProvider from configuration."""

    if name == "mock":
        return MockModelProvider()

    if name == "deepseek":
        ds_cfg = cfg.get("deepseek", {})
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            logger.warning("DEEPSEEK_API_KEY not set — falling back to mock")
            return MockModelProvider()
        provider = DeepSeekProvider(
            model=ds_cfg.get("model", "deepseek-chat"),
            temperature=ds_cfg.get("temperature", 0.0),
            api_key=api_key,
        )
        provider._actual_name = "deepseek"  # type: ignore[attr-defined]
        return provider

    if name == "gemini":
        gm_cfg = cfg.get("gemini", {})
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set — falling back to mock")
            return MockModelProvider()
        provider = GeminiProvider(
            model=gm_cfg.get("model", "gemini-2.0-flash"),
            temperature=gm_cfg.get("temperature", 0.0),
            api_key=api_key,
        )
        provider._actual_name = "gemini"  # type: ignore[attr-defined]
        return provider

    if name == "fallback":
        fb_cfg = cfg.get("fallback", {})
        order = fb_cfg.get("order", ["deepseek", "gemini"])
        providers: list[ModelProvider] = []

        for pname in order:
            if pname == "deepseek":
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                if api_key:
                    ds_cfg = cfg.get("deepseek", {})
                    providers.append(DeepSeekProvider(
                        model=ds_cfg.get("model", "deepseek-chat"),
                        temperature=ds_cfg.get("temperature", 0.0),
                        api_key=api_key,
                    ))
                else:
                    logger.info("Skipping deepseek — no API key")
            elif pname == "gemini":
                api_key = os.environ.get("GEMINI_API_KEY", "")
                if api_key:
                    gm_cfg = cfg.get("gemini", {})
                    providers.append(GeminiProvider(
                        model=gm_cfg.get("model", "gemini-2.0-flash"),
                        temperature=gm_cfg.get("temperature", 0.0),
                        api_key=api_key,
                    ))
                else:
                    logger.info("Skipping gemini — no API key")

        if not providers:
            logger.warning("No real providers available in fallback — using mock")
            return MockModelProvider()

        mock = MockModelProvider()
        provider = FallbackProvider(providers, mock=mock)
        provider._actual_name = "fallback"  # type: ignore[attr-defined]
        logger.info(
            "Fallback provider: %s → mock",
            " → ".join(type(p).__name__ for p in providers),
        )
        return provider

    logger.warning("Unknown provider '%s' — falling back to mock", name)
    return MockModelProvider()

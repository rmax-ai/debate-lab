"""Harness registry loader — reads agent definitions from YAML/JSON files."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from debate_harnesses.schemas import AgentHarness, HarnessRegistry


class HarnessLoader:
    """Load harness definitions from filesystem or inline config."""

    @staticmethod
    def from_yaml(path: str | Path) -> HarnessRegistry:
        """Load harness definitions from a YAML file.

        Expected format:
            harnesses:
              - id: advocate
                name: Advocate
                role: "Argue for..."
                model: mock
                tools_allowed: [web_search]
        """
        raw = yaml.safe_load(Path(path).read_text())
        return HarnessRegistry.model_validate(raw)

    @staticmethod
    def from_json(path: str | Path) -> HarnessRegistry:
        """Load harness definitions from a JSON file."""
        raw = json.loads(Path(path).read_text())
        return HarnessRegistry.model_validate(raw)

    @staticmethod
    def from_dict(data: dict) -> HarnessRegistry:
        """Load harness definitions from a dict."""
        return HarnessRegistry.model_validate(data)

    @staticmethod
    def from_harnesses(harnesses: list[AgentHarness]) -> HarnessRegistry:
        """Create a registry from a list of harness objects."""
        return HarnessRegistry(harnesses=harnesses)

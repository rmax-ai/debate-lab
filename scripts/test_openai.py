"""Quick smoke test for OpenAIProvider with native structured output."""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "packages" / "harnesses" / "src"))

from pydantic import BaseModel, Field
from debate_harnesses.real_providers import OpenAIProvider


class TestResponse(BaseModel):
    model_config = {"extra": "forbid"}
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_points: list[str]


async def main():
    # Get API key securely via pass (never enters our output)
    proc = subprocess.run(
        ["pass", "show", "hermes/openai/api-key"],
        capture_output=True, text=True, timeout=10,
        env={"PASSWORD_STORE_DIR": os.path.expanduser("~/.hermes/.password-store")},
    )
    api_key = proc.stdout.strip()
    if not api_key:
        print("ERROR: No API key")
        sys.exit(1)

    provider = OpenAIProvider(api_key=api_key)
    print(f"Provider: gpt-4o-mini | temp={provider.temperature}")
    print("Calling generate() with native structured output...")

    result = await provider.generate(
        "What is the capital of France? Answer concisely.",
        TestResponse,
    )
    print(f"✓ summary:  {result.summary}")
    print(f"✓ confidence: {result.confidence}")
    print(f"✓ key_points ({len(result.key_points)}): {result.key_points}")
    print(f"\nOpenAIProvider works! call_count={provider.call_count}")


if __name__ == "__main__":
    asyncio.run(main())

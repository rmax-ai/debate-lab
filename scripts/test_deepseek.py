"""Quick smoke test for DeepSeekProvider."""
import asyncio
import os
import sys
from pathlib import Path

# Add packages to path
repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root / "packages" / "harnesses" / "src"))
sys.path.insert(0, str(repo_root / "packages" / "orchestrator" / "src"))
sys.path.insert(0, str(repo_root / "packages" / "tracing" / "src"))
sys.path.insert(0, str(repo_root / "packages" / "tools" / "src"))
sys.path.insert(0, str(repo_root / "packages" / "evidence" / "src"))

from pydantic import BaseModel, Field
from debate_harnesses.real_providers import DeepSeekProvider


class TestResponse(BaseModel):
    model_config = {"extra": "forbid"}
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_points: list[str]


async def main():
    # Read key from temp file (avoids terminal redaction)
    api_key = Path("/tmp/dl_key.txt").read_text().strip()
    if not api_key:
        print("ERROR: No API key in /tmp/dl_key.txt")
        sys.exit(1)

    provider = DeepSeekProvider(api_key=api_key)
    print(f"Provider: deepseek-chat | temp={provider.temperature}")
    print("Calling generate()...")

    result = await provider.generate(
        "What is the capital of France? Answer concisely.",
        TestResponse,
    )
    print(f"✓ summary:  {result.summary}")
    print(f"✓ confidence: {result.confidence}")
    print(f"✓ key_points ({len(result.key_points)}): {result.key_points}")
    print(f"\nDeepSeekProvider works! call_count={provider.call_count}")


if __name__ == "__main__":
    asyncio.run(main())

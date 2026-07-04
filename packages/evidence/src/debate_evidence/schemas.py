"""Evidence and claim schemas for DebateLab."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ClaimStatus(StrEnum):
    """Lifecycle states for a claim."""

    PROPOSED = "proposed"
    CHALLENGED = "challenged"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    ACCEPTED = "accepted"
    UNRESOLVED = "unresolved"


class EvidenceRef(BaseModel):
    """Reference to a piece of evidence gathered during a debate."""

    model_config = {"extra": "forbid", "frozen": True}

    id: str = Field(..., pattern=r"^E-\d+$", description="Evidence ID, e.g. E-08")
    source_type: str = Field(..., pattern=r"^(web_search|doc_search|code_search)$")
    url: str | None = None
    title: str = Field(..., min_length=1)
    quote_or_excerpt: str = Field(..., min_length=1)
    extracted_facts: list[str] = Field(default_factory=list)
    reliability_score: float = Field(default=0.5, ge=0.0, le=1.0)
    retrieved_by: str = Field(..., pattern=r"^[a-z_]+$")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("reliability_score")
    @classmethod
    def _round_score(cls, v: float) -> float:
        return round(v, 2)


class Claim(BaseModel):
    """A structured claim made by an agent during debate."""

    model_config = {"extra": "forbid", "frozen": True}

    id: str = Field(..., pattern=r"^C-\d+$", description="Claim ID, e.g. C-17")
    text: str = Field(..., min_length=1, max_length=2000)
    agent_id: str = Field(..., pattern=r"^[a-z_]+$")
    status: ClaimStatus = ClaimStatus.PROPOSED
    evidence_refs: list[str] = Field(default_factory=list)
    challenged_by: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    revisions: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def _round_confidence(cls, v: float | None) -> float | None:
        if v is not None:
            return round(v, 2)
        return v

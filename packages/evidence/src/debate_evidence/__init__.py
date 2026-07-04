"""Evidence extraction and scoring for DebateLab."""

from debate_evidence.extractor import EvidenceExtractor
from debate_evidence.schemas import Claim, ClaimStatus, EvidenceRef

__all__ = [
    "Claim",
    "ClaimStatus",
    "EvidenceExtractor",
    "EvidenceRef",
]

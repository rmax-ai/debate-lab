"""Tests for evidence schemas."""

import pytest
from pydantic import ValidationError

from debate_evidence.schemas import Claim, ClaimStatus, EvidenceRef


class TestEvidenceRef:
    def test_valid_minimal(self):
        ref = EvidenceRef(
            id="E-01",
            source_type="web_search",
            title="Test Result",
            quote_or_excerpt="Some excerpt",
            retrieved_by="advocate",
        )
        assert ref.id == "E-01"
        assert ref.reliability_score == 0.5

    def test_invalid_id_pattern(self):
        with pytest.raises(ValidationError):
            EvidenceRef(
                id="bad",
                source_type="web_search",
                title="X",
                quote_or_excerpt="X",
                retrieved_by="advocate",
            )

    def test_reliability_score_rounded(self):
        ref = EvidenceRef(
            id="E-01",
            source_type="web_search",
            title="X",
            quote_or_excerpt="X",
            retrieved_by="advocate",
            reliability_score=0.876,
        )
        assert ref.reliability_score == 0.88

    def test_immutable(self):
        ref = EvidenceRef(
            id="E-01",
            source_type="web_search",
            title="X",
            quote_or_excerpt="X",
            retrieved_by="advocate",
        )
        with pytest.raises((TypeError, ValueError)):
            ref.title = "new"  # frozen model


class TestClaim:
    def test_valid_default(self):
        claim = Claim(id="C-01", text="A test claim", agent_id="advocate")
        assert claim.status == ClaimStatus.PROPOSED
        assert claim.evidence_refs == []
        assert claim.confidence is None

    def test_invalid_id(self):
        with pytest.raises(ValidationError):
            Claim(id="bad", text="X", agent_id="advocate")

    def test_confidence_rounded(self):
        claim = Claim(id="C-01", text="X", agent_id="advocate", confidence=0.876)
        assert claim.confidence == 0.88

    def test_immutable(self):
        claim = Claim(id="C-01", text="X", agent_id="advocate")
        with pytest.raises((TypeError, ValueError)):
            claim.status = ClaimStatus.ACCEPTED  # frozen model


class TestClaimStatus:
    def test_all_statuses(self):
        assert ClaimStatus.PROPOSED == "proposed"
        assert ClaimStatus.CHALLENGED == "challenged"
        assert ClaimStatus.SUPPORTED == "supported"
        assert ClaimStatus.WEAKENED == "weakened"
        assert ClaimStatus.ACCEPTED == "accepted"
        assert ClaimStatus.UNRESOLVED == "unresolved"

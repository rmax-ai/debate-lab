"""Tests for the claim tracker."""

import pytest
from debate_evidence.schemas import ClaimStatus

from debate_orchestrator.claim_tracker import ClaimTracker


class TestClaimTracker:
    def test_add_claim(self):
        tracker = ClaimTracker()
        claim = tracker.add_claim("Test claim", "advocate")
        assert claim.id == "C-01"
        assert claim.text == "Test claim"
        assert claim.status == ClaimStatus.PROPOSED

    def test_get_claim(self):
        tracker = ClaimTracker()
        tracker.add_claim("C1", "a")
        tracker.add_claim("C2", "b")
        assert tracker.get("C-01").text == "C1"
        assert tracker.get("C-02").text == "C2"
        assert tracker.get("C-99") is None

    def test_all_claims(self):
        tracker = ClaimTracker()
        tracker.add_claim("C1", "a")
        tracker.add_claim("C2", "b")
        assert len(tracker.all_claims()) == 2

    def test_claims_by_agent(self):
        tracker = ClaimTracker()
        tracker.add_claim("C1", "advocate")
        tracker.add_claim("C2", "skeptic")
        tracker.add_claim("C3", "advocate")
        assert len(tracker.claims_by_agent("advocate")) == 2
        assert len(tracker.claims_by_agent("skeptic")) == 1

    def test_claims_by_status(self):
        tracker = ClaimTracker()
        c1 = tracker.add_claim("C1", "a")
        tracker.add_claim("C2", "b")
        tracker.challenge(c1.id, "b", "Objection!")
        challenged = tracker.claims_by_status(ClaimStatus.CHALLENGED)
        assert len(challenged) == 1
        assert challenged[0].id == "C-01"

    def test_link_evidence(self):
        tracker = ClaimTracker()
        claim = tracker.add_claim("C1", "a")
        tracker.link_evidence(claim.id, ["E-01", "E-02"])
        updated = tracker.get(claim.id)
        assert "E-01" in updated.evidence_refs
        assert "E-02" in updated.evidence_refs

    def test_challenge(self):
        tracker = ClaimTracker()
        claim = tracker.add_claim("C1", "advocate")
        tracker.challenge(claim.id, "skeptic", "Weak evidence")
        updated = tracker.get(claim.id)
        assert updated.status == ClaimStatus.CHALLENGED
        assert "skeptic" in updated.challenged_by
        assert "Weak evidence" in updated.objections

    def test_update_status(self):
        tracker = ClaimTracker()
        claim = tracker.add_claim("C1", "a")
        tracker.update_status(claim.id, ClaimStatus.SUPPORTED, confidence=0.9)
        updated = tracker.get(claim.id)
        assert updated.status == ClaimStatus.SUPPORTED
        assert updated.confidence == 0.9

    def test_revoke(self):
        tracker = ClaimTracker()
        claim = tracker.add_claim("C1", "a")
        tracker.revoke(claim.id, "Changed position after evidence")
        updated = tracker.get(claim.id)
        assert updated.status == ClaimStatus.WEAKENED
        assert "Changed position after evidence" in updated.revisions

    def test_stats(self):
        tracker = ClaimTracker()
        tracker.add_claim("C1", "advocate")
        tracker.add_claim("C2", "skeptic")
        tracker.add_claim("C3", "advocate")
        stats = tracker.stats()
        assert stats["total"] == 3
        assert stats["by_agent"]["advocate"] == 2
        assert stats["by_agent"]["skeptic"] == 1
        assert stats["by_status"]["proposed"] == 3

    def test_get_unknown_raises(self):
        tracker = ClaimTracker()
        with pytest.raises(KeyError):
            tracker.challenge("C-99", "skeptic", "?")

    def test_sequential_ids(self):
        tracker = ClaimTracker()
        c1 = tracker.add_claim("a", "x")
        c2 = tracker.add_claim("b", "x")
        c3 = tracker.add_claim("c", "x")
        assert c1.id == "C-01"
        assert c2.id == "C-02"
        assert c3.id == "C-03"

    def test_duplicate_evidence_links_deduplicated(self):
        tracker = ClaimTracker()
        claim = tracker.add_claim("C1", "a")
        tracker.link_evidence(claim.id, ["E-01"])
        tracker.link_evidence(claim.id, ["E-01", "E-02"])
        updated = tracker.get(claim.id)
        assert len(updated.evidence_refs) == 2

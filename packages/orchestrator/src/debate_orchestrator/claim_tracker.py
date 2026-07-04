"""Claim tracker — manages claim lifecycle during a debate run."""

from __future__ import annotations

from debate_evidence.schemas import Claim, ClaimStatus


class ClaimTracker:
    """Tracks claims, their evidence links, challenges, and status changes.

    This is the authoritative in-memory view of all claims for a debate run.
    For persistence, events are emitted and stored in the event log.
    """

    def __init__(self) -> None:
        self._claims: dict[str, Claim] = {}
        self._next_id: int = 1

    def add_claim(self, text: str, agent_id: str, **kwargs) -> Claim:
        """Create and register a new claim."""
        claim_id = f"C-{self._next_id:02d}"
        self._next_id += 1
        claim = Claim(id=claim_id, text=text, agent_id=agent_id, **kwargs)
        self._claims[claim_id] = claim
        return claim

    def get(self, claim_id: str) -> Claim | None:
        """Get a claim by ID."""
        return self._claims.get(claim_id)

    def all_claims(self) -> list[Claim]:
        """All claims in insertion order."""
        return list(self._claims.values())

    def claims_by_agent(self, agent_id: str) -> list[Claim]:
        """Claims made by a specific agent."""
        return [c for c in self._claims.values() if c.agent_id == agent_id]

    def claims_by_status(self, status: ClaimStatus) -> list[Claim]:
        """Claims with a specific status."""
        return [c for c in self._claims.values() if c.status == status]

    def link_evidence(self, claim_id: str, evidence_ref_ids: list[str]) -> None:
        """Link evidence refs to a claim."""
        claim = self._get_or_raise(claim_id)
        claim = Claim(
            id=claim.id,
            text=claim.text,
            agent_id=claim.agent_id,
            status=claim.status,
            evidence_refs=list(set(claim.evidence_refs + evidence_ref_ids)),
            challenged_by=claim.challenged_by,
            objections=claim.objections,
            revisions=claim.revisions,
            confidence=claim.confidence,
        )
        self._claims[claim_id] = claim

    def challenge(self, claim_id: str, challenger_id: str, objection: str) -> None:
        """Record a challenge against a claim."""
        claim = self._get_or_raise(claim_id)
        claim = Claim(
            id=claim.id,
            text=claim.text,
            agent_id=claim.agent_id,
            status=ClaimStatus.CHALLENGED,
            evidence_refs=claim.evidence_refs,
            challenged_by=sorted(set(claim.challenged_by) | {challenger_id}),
            objections=sorted(set(claim.objections) | {objection}),
            revisions=claim.revisions,
            confidence=claim.confidence,
        )
        self._claims[claim_id] = claim

    def update_status(self, claim_id: str, status: ClaimStatus, **kwargs) -> None:
        """Update a claim's status and optionally other fields."""
        claim = self._get_or_raise(claim_id)
        updates = {
            "id": claim.id,
            "text": claim.text,
            "agent_id": claim.agent_id,
            "status": status,
            "evidence_refs": kwargs.get("evidence_refs", claim.evidence_refs),
            "challenged_by": kwargs.get("challenged_by", claim.challenged_by),
            "objections": kwargs.get("objections", claim.objections),
            "revisions": kwargs.get("revisions", claim.revisions),
            "confidence": kwargs.get("confidence", claim.confidence),
        }
        self._claims[claim_id] = Claim(**updates)

    def revoke(self, claim_id: str, revision_note: str) -> None:
        """Mark a claim as revised with a note."""
        claim = self._get_or_raise(claim_id)
        claim = Claim(
            id=claim.id,
            text=claim.text,
            agent_id=claim.agent_id,
            status=ClaimStatus.WEAKENED,
            evidence_refs=claim.evidence_refs,
            challenged_by=claim.challenged_by,
            objections=claim.objections,
            revisions=sorted(set(claim.revisions) | {revision_note}),
            confidence=claim.confidence,
        )
        self._claims[claim_id] = claim

    def stats(self) -> dict:
        """Summary statistics about tracked claims."""
        claims = list(self._claims.values())
        by_status: dict[str, int] = {}
        by_agent: dict[str, int] = {}
        for c in claims:
            by_status[c.status.value] = by_status.get(c.status.value, 0) + 1
            by_agent[c.agent_id] = by_agent.get(c.agent_id, 0) + 1
        return {
            "total": len(claims),
            "by_status": by_status,
            "by_agent": by_agent,
        }

    def _get_or_raise(self, claim_id: str) -> Claim:
        claim = self._claims.get(claim_id)
        if not claim:
            raise KeyError(f"Claim '{claim_id}' not found")
        return claim

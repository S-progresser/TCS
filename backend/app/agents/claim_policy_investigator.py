from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.deterministic import calculate_deductible_and_payout
from backend.app.retriever import load_claims, load_rulebooks, retrieve_guidance


@dataclass
class InvestigationResult:
    claim: dict[str, Any]
    evidence: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    rule_hits: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    language: str = "en"


class ClaimPolicyInvestigator:
    async def investigate(self, claim_id: str, normalized_query: str, language: str = "en") -> InvestigationResult:
        claim = next((item for item in load_claims() if item["id"] == claim_id), None)
        if claim is None:
            raise ValueError(f"Unknown claim id: {claim_id}")

        guidance = retrieve_guidance(
            " ".join((normalized_query, str(claim.get("product", "")), str(claim.get("summary", ""))))
        )
        rulebooks = load_rulebooks()
        relevant_rules = [rule for rule in rulebooks if any(keyword in normalized_query for keyword in rule.keywords) or rule.category in {"documents", "coverage"}]
        deductions = calculate_deductible_and_payout(claim)
        facts = [
            f"Claim {claim['id']} is currently {claim.get('status', 'in review')}.",
            f"Product: {claim.get('product', 'unknown')} | Policy: {claim.get('policy_number', 'unknown')}",
            f"Claim amount: ₹{claim.get('claim_amount', 0):,.0f} | Deductible: ₹{deductions['deductible']:.0f} | Estimated payout: ₹{deductions['estimated_payout']:.0f}",
        ]

        evidence = [result.snippet for result in guidance[:3]]
        citations = [result.source for result in guidance[:3]]
        rule_hits = [rule.title for rule in relevant_rules[:3]]

        return InvestigationResult(
            claim=claim,
            evidence=evidence,
            citations=citations,
            rule_hits=rule_hits,
            facts=facts,
            language=language,
        )

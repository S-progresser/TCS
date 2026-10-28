from __future__ import annotations

import asyncio
from typing import Any

from backend.app.agents.claim_policy_investigator import ClaimPolicyInvestigator
from backend.app.agents.concierge import ConciergeAgent
from backend.app.agents.document_analyst import DocumentAnalyst
from backend.app.agents.explainer_verifier import ExplainerVerifier
from backend.app.deterministic import calculate_deductible_and_payout
from backend.app.retriever import load_claims
from backend.app.schemas import ClaimAnalysis, DocumentReview, QueryResponse


def get_claim_by_id(claim_id: str) -> dict[str, Any] | None:
    for claim in load_claims():
        if claim["id"] == claim_id:
            return claim
    return None


def calculate_readiness(claim: dict[str, Any]) -> ClaimAnalysis:
    checks = [
        "Hospital discharge summary submitted",
        "Original bill and invoice attached",
        "KYC verification complete",
        "Claim form signed and notarized",
        "Final settlement amount verified",
    ]
    completed = claim.get("checklist", [])
    pending = [item for item in checks if item not in completed]
    total = len(checks)
    score = max(35, round((len(completed) / total) * 100))
    payout = calculate_deductible_and_payout(claim)
    deductible = payout["deductible"]
    copay = payout["copay"]
    estimate = payout["estimated_payout"]
    return ClaimAnalysis(
        claim_id=claim["id"],
        readiness_score=score,
        status=claim.get("status", "in_review"),
        summary=claim.get("summary", "Claim in review"),
        checklist=completed or checks[:2],
        next_steps=[
            "Upload the missing discharge summary and final bill.",
            "Confirm treatment dates and provider details.",
            "Follow up with the hospital for the original invoice.",
        ],
        deductible=float(deductible),
        copay=float(copay),
        estimated_payout=max(0, float(estimate)),
        risk_flags=[item for item in ["Missing discharge summary", "Pending invoice verification"] if item in pending],
    )


def validate_document(filename: str, text: str | None = None) -> DocumentReview:
    name = (filename or "document.pdf").lower()
    missing: list[str] = []
    mismatches: list[str] = []
    if ".pdf" not in name and ".png" not in name and ".jpg" not in name and ".jpeg" not in name:
        missing.append("Unsupported file format")
    if text:
        lower = text.lower()
        if "hospital" not in lower and "claim" not in lower:
            mismatches.append("Document does not appear to reference the claim or hospitalization")

        has_invoice_reference = "invoice" in lower or "bill" in lower
        has_discharge_reference = "discharge" in lower
        has_negative_invoice = "no invoice" in lower or "invoice not" in lower or "no billing" in lower or "bill not" in lower
        has_negative_discharge = "no discharge" in lower or "discharge not" in lower or "discharge summary missing" in lower

        if not has_invoice_reference or has_negative_invoice:
            missing.append("Invoice or bill not found")
        if not has_discharge_reference or has_negative_discharge:
            missing.append("Discharge summary missing")
    if not missing and not mismatches:
        return DocumentReview(
            filename=filename,
            valid=True,
            score=92,
            missing_documents=[],
            mismatches=[],
            next_steps=["Proceed to verification", "Match bill entries to the claim summary"],
        )
    return DocumentReview(
        filename=filename,
        valid=False,
        score=58,
        missing_documents=missing,
        mismatches=mismatches,
        next_steps=["Upload the final discharge summary", "Share the insurer-approved invoice copy"],
    )


async def answer_query(claim_id: str, question: str, language: str = "en", document_context: str | None = None) -> QueryResponse:
    claim = get_claim_by_id(claim_id)
    if claim is None:
        raise ValueError(f"Unknown claim id: {claim_id}")

    concierge = ConciergeAgent()
    plan = concierge.plan(question, claim_id=claim_id, document_context=document_context).plan

    if plan.language != language:
        plan.language = language

    investigator = ClaimPolicyInvestigator()
    document_analyst = DocumentAnalyst()
    explainer_verifier = ExplainerVerifier()

    investigator_task = investigator.investigate(claim_id, plan.normalized_query, plan.language)
    document_task = None
    if plan.needs_document_analysis and document_context is not None:
        document_task = document_analyst.analyze(filename="uploaded-document", text=document_context, claim=claim)

    if document_task is None:
        investigation = await investigator_task
        final_response = await explainer_verifier.compose(
            claim=claim,
            investigation=investigation,
            plan=plan,
            fallback_answer=(
                f"Your claim {claim['id']} is currently in {claim['status']} status. Based on the insurer's policy rules, "
                "the next required action is to submit the final discharge summary and invoice to close the document review step."
            ),
        )
        return final_response

    investigation, document_result = await asyncio.gather(investigator_task, document_task)
    final_response = await explainer_verifier.compose(
        claim=claim,
        investigation=investigation,
        document_review=document_result,
        plan=plan,
        fallback_answer=(
            f"Your claim {claim['id']} is currently in {claim['status']} status. Based on the insurer's policy rules, "
            "the next required action is to submit the final discharge summary and invoice to close the document review step."
        ),
    )
    return final_response

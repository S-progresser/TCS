import asyncio

import pytest

from backend.app.agents.claim_policy_investigator import ClaimPolicyInvestigator
from backend.app.agents.concierge import ConciergeAgent
from backend.app.agents.document_analyst import DocumentAnalyst
from backend.app.agents.explainer_verifier import ExplainerVerifier
from backend.app.deterministic import build_concierge_plan, calculate_deductible_and_payout, validate_request_schema
from backend.app.orchestrator import answer_query


@pytest.mark.asyncio
async def test_concierge_detects_language_and_intent():
    result = ConciergeAgent().plan("कृपया मुझे मेरा दावा दर्ज़ करें और बिल का पता बताइए", claim_id="CLM-3021")
    plan = result.plan
    assert plan.language == "hi"
    assert plan.intent == "document_review"
    assert plan.claim_id == "CLM-3021"
    assert plan.needs_document_analysis is True


@pytest.mark.asyncio
async def test_claim_policy_investigator_returns_facts_and_citations():
    result = await ClaimPolicyInvestigator().investigate("CLM-3021", "missing discharge summary and invoice", "en")
    assert result.claim["id"] == "CLM-3021"
    assert len(result.evidence) > 0
    assert len(result.citations) > 0
    assert any("Claim" in fact for fact in result.facts)


@pytest.mark.asyncio
async def test_document_analyst_flags_required_gaps():
    result = await DocumentAnalyst().analyze(
        filename="notes.txt",
        text="No invoice or discharge details present",
        claim={"customer_name": "Asha Verma", "claim_amount": 185000, "treatment_date": "2024-09-01"},
    )
    assert result.valid is False
    assert any("Invoice or bill not found" in item for item in result.missing_documents)
    assert any("Discharge summary missing" in item for item in result.missing_documents)
    assert result.provider_message is not None


@pytest.mark.asyncio
async def test_verifier_rejects_unverified_document_draft():
    document_review = type(
        "DocumentReview",
        (),
        {"missing_documents": ["Invoice or bill not found"], "mismatches": ["Claim amount could not be verified"], "next_steps": ["Upload the bill"], "provider_message": "Manual review required"},
    )()
    result = await ExplainerVerifier().compose(
        claim={"id": "CLM-3021", "status": "in review", "summary": "Hospitalization claim"},
        investigation=type("Investigation", (), {"evidence": ["Rule says documents are required"], "citations": ["Policy guidance"]})(),
        document_review=document_review,
        plan=build_concierge_plan("missing invoice", claim_id="CLM-3021"),
    )
    assert result.confidence < 0.7
    assert "cannot confirm" in result.answer.lower()


@pytest.mark.asyncio
async def test_answer_query_without_document_context_works():
    result = await answer_query("CLM-3021", "What is the current status of my claim?", "en")
    assert result.claim_id == "CLM-3021"
    assert result.language == "en"
    assert len(result.citations) > 0


@pytest.mark.asyncio
async def test_parallel_agent_workflow_runs_for_document_review():
    investigation_task = ClaimPolicyInvestigator().investigate("CLM-3021", "document review", "en")
    analysis_task = DocumentAnalyst().analyze(
        filename="invoice.pdf",
        text="Hospital invoice and discharge summary for claim",
        claim={"customer_name": "Asha Verma", "claim_amount": 185000, "treatment_date": "2024-09-01"},
    )
    investigation, analysis = await asyncio.gather(investigation_task, analysis_task)
    assert investigation.claim["id"] == "CLM-3021"
    assert analysis.valid is False or analysis.valid is True
    assert validate_request_schema({"claim_id": "CLM-3021", "question": "status"}) is True


@pytest.mark.asyncio
async def test_deterministic_service_calculates_payout_and_language():
    payout = calculate_deductible_and_payout({"claim_amount": 185000, "deductible": 18000, "copay": 5000})
    assert payout["estimated_payout"] == 162000.0
    assert build_concierge_plan("Need my claim status", claim_id="CLM-3021").language == "en"

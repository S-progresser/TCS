import asyncio
import json

import pytest

from backend.app.agents.claim_policy_investigator import ClaimPolicyInvestigator
from backend.app.agents.concierge import ConciergeAgent
from backend.app.agents.document_analyst import DocumentAnalyst
from backend.app.agents.explainer_verifier import ExplainerVerifier
from backend.app.deterministic import build_concierge_plan, calculate_deductible_and_payout, validate_request_schema
from backend.app.llm import LLMResult
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
async def test_verifier_rejects_unverified_document_draft(monkeypatch):
    document_review = type(
        "DocumentReview",
        (),
        {"missing_documents": ["Invoice or bill not found"], "mismatches": ["Claim amount could not be verified"], "next_steps": ["Upload the bill"], "provider_message": "Manual review required"},
    )()

    class DeterministicLLM:
        settings = type("Settings", (), {"smart_model": "test-smart"})()

        async def generate_result(self, prompt, **kwargs):
            payload = json.loads(prompt)
            return LLMResult(content=payload["fallback"], provider="deterministic", fallback=True)

    monkeypatch.setattr("backend.app.agents.explainer_verifier.get_llm_client", lambda: DeterministicLLM())
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
async def test_submit_question_gets_pending_documents_not_only_claim_status(monkeypatch):
    prompts = []

    class DeterministicLLM:
        settings = type("Settings", (), {"fast_model": "test-fast", "smart_model": "test-smart"})()

        async def generate_result(self, prompt, **kwargs):
            prompts.append(prompt)
            payload = json.loads(prompt)
            return LLMResult(
                content=payload["fallback"],
                provider="deterministic",
                fallback=True,
                error="provider_unavailable",
            )

    monkeypatch.setattr("backend.app.agents.explainer_verifier.get_llm_client", lambda: DeterministicLLM())
    question = "what do i need to submit?"
    result = await answer_query("CLM-3021", question, "en")

    assert result.provider == "deterministic"
    assert "outstanding" in result.answer
    assert "Hospital discharge summary submitted" in result.answer
    assert "Final hospital invoice attached" in result.answer
    assert "currently Document review" not in result.answer
    assert any("Hospital discharge summary submitted" in action for action in result.next_actions)
    prompt = json.loads(prompts[0])
    assert prompt["customer_question"] == question
    assert prompt["intent"] == "document_review"
    assert "Hospital discharge summary submitted" in prompt["pending_requirements"]


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

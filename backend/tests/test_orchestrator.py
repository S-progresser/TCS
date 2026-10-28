import pytest

from backend.app.orchestrator import answer_query, calculate_readiness


@pytest.mark.asyncio
async def test_answer_query_for_status():
    response = await answer_query("CLM-3021", "What is the status of my claim?", "en")
    assert response.claim_id == "CLM-3021"
    assert "status" in response.answer.lower() or "document" in response.answer.lower()


def test_calculate_readiness():
    claim = {
        "id": "CLM-1234",
        "status": "Document review",
        "summary": "Document review in progress",
        "claim_amount": 150000,
        "deductible": 20000,
        "copay": 5000,
        "checklist": [
            "Hospital discharge summary submitted",
            "Original bill and invoice attached",
            "KYC verification complete"
        ],
    }
    result = calculate_readiness(claim)
    assert result.readiness_score >= 50
    assert result.estimated_payout > 0

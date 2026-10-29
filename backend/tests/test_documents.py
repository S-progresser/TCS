from __future__ import annotations

import asyncio
import json
from io import BytesIO

import pymupdf
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.events import document_event_stream, get_document_event_store, publish_document_event
from backend.app.llm import LLMResult
from backend.app.orchestrator import calculate_readiness, validate_document
from backend.main import app

client = TestClient(app)


def make_pdf(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def post_pdf(text: str, *, session: str = "upload-test", claim_id: str = "CLM-3021"):
    return client.post(
        "/api/documents/process",
        data={"session_id": session, "claim_id": claim_id},
        files={"file": ("invoice.pdf", make_pdf(text), "application/pdf")},
    )


def stream_events(session: str):
    async def collect():
        messages = [event async for event in document_event_stream(session)]
        return [json.loads(event["data"]) for event in messages]

    return asyncio.run(collect())


def test_validate_document_legacy_contract():
    assert validate_document("invoice.pdf", "Hospital invoice for claim and discharge summary").valid
    result = validate_document("notes.txt", "No invoice or discharge details present")
    assert result.valid is False
    assert any("Invoice or bill not found" in item for item in result.missing_documents)


def test_upload_extracts_real_pdf_and_emits_confirmed_stages():
    response = post_pdf(
        "Hospital invoice\nPatient: Asha Reddy\nHospital: City Hospital\n"
        "Invoice date: 2026-10-28\nBill amount: Rs. 185000\nRoom charges Rs. 50000",
    )
    assert response.status_code == 200
    result = response.json()
    assert result["claim_id"] == "CLM-3021"
    assert result["extraction_status"] == "extracted"
    assert result["extracted_document_type"] == "invoice"
    assert result["extracted_fields"]["claimant_name"] == "Asha Reddy"
    assert result["extracted_fields"]["amount"] == "185000"
    assert any("discharge summary" in item.lower() for item in result["missing_documents"])

    events = stream_events("upload-test")
    assert [event["stage"] for event in events if event["type"] == "document.progress"] == [
        "received", "reading", "reading", "extracting", "extracting",
        "requirements", "requirements", "claim_compare", "claim_compare", "explanation",
    ]
    assert events[-1]["type"] == "document.completed"
    assert events[-1]["status"] == "completed"
    completed_stages = {event["stage"] for event in events if event["status"] == "completed"}
    assert completed_stages == {"received", "reading", "extracting", "requirements", "claim_compare", "explanation"}
    assert not any(event.get("progress") == 100 for event in events)


def test_upload_rejects_unsupported_and_mismatched_content():
    unsupported = client.post(
        "/api/documents/process",
        data={"session_id": "unsupported-test", "claim_id": "CLM-3021"},
        files={"file": ("notes.txt", b"Hospital invoice", "text/plain")},
    )
    assert unsupported.status_code == 415
    assert "supported PDF" in unsupported.json()["detail"]

    mismatch = client.post(
        "/api/documents/process",
        data={"session_id": "mismatch-type-test", "claim_id": "CLM-3021"},
        files={"file": ("invoice.pdf", b"not a pdf", "application/pdf")},
    )
    assert mismatch.status_code == 415


def test_unreadable_pdf_does_not_turn_extraction_failure_into_missing_fields():
    response = client.post(
        "/api/documents/process",
        data={"session_id": "blank-pdf-test", "claim_id": "CLM-3021"},
        files={"file": ("scan.pdf", make_pdf(""), "application/pdf")},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["extraction_status"] == "unreadable"
    assert "scanned document" in result["extraction_message"]
    assert result["missing_documents"] == []
    assert result["fields_unverified"] == ["Document contents"]
    events = stream_events("blank-pdf-test")
    assert events[-1]["type"] == "document.failed"
    assert events[-1]["status"] == "failed"


def test_deterministic_findings_finish_when_groq_drafting_falls_back(monkeypatch):
    class FallbackLLM:
        settings = type("Settings", (), {"fast_model": "openai/gpt-oss-20b", "replay": False})()

        async def generate_result(self, *args, **kwargs):
            return LLMResult(
                content="Live AI assistance is unavailable.",
                provider="deterministic",
                error="timeout",
                fallback=True,
            )

    monkeypatch.setattr("backend.app.document_processing.get_llm_client", lambda: FallbackLLM())
    response = post_pdf(
        "Hospital invoice\nPatient: Asha Reddy\nBill amount: Rs. 185000\nRoom charges Rs. 50000",
        session="groq-fallback-terminal-test",
    )
    assert response.status_code == 200
    result = response.json()
    assert result["extraction_status"] == "extracted"
    assert result["provider"] == "deterministic"
    assert result["next_steps"]
    events = stream_events("groq-fallback-terminal-test")
    assert events[-1]["type"] == "document.completed"
    assert events[-1]["result"]["provider"] == "deterministic"
    assert {event["stage"] for event in events if event["status"] == "completed"} == {
        "received", "reading", "extracting", "requirements", "claim_compare", "explanation",
    }


def test_actual_name_and_amount_mismatches_are_reported():
    response = post_pdf(
        "Hospital invoice\nPatient: Different Patient\nHospital: City Hospital\n"
        "Bill amount: Rs. 125000\nitemized medicine Rs. 5000",
        session="mismatch-fields-test",
    )
    result = response.json()
    assert any("does not match the claim record" in item for item in result["mismatches"])
    assert any("differs from the claim amount" in item for item in result["mismatches"])


def test_replacement_upload_is_analyzed_as_a_new_session():
    first = post_pdf("Hospital invoice\nPatient: Asha Reddy\nBill amount: Rs. 185000\nRoom charge Rs. 50000", session="replace-one")
    second = post_pdf("Hospital discharge summary\nPatient: Asha Reddy\nDischarge date: 2026-10-28", session="replace-two")
    assert first.status_code == second.status_code == 200
    assert first.json()["extracted_document_type"] == "invoice"
    assert second.json()["extracted_document_type"] == "discharge_summary"
    assert get_document_event_store("replace-one")[-1]["session_id"] == "replace-one"
    assert get_document_event_store("replace-two")[-1]["session_id"] == "replace-two"


def test_upload_size_limit_and_claim_association():
    too_large = client.post(
        "/api/documents/process",
        data={"session_id": "large-test", "claim_id": "CLM-3021"},
        files={"file": ("large.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024 + 1), "application/pdf")},
    )
    assert too_large.status_code == 413
    unknown_claim = client.post(
        "/api/documents/process",
        data={"session_id": "unknown-claim-test", "claim_id": "CLM-0000"},
        files={"file": ("invoice.pdf", make_pdf("Hospital invoice\nPatient: Sample\nBill amount: 10"), "application/pdf")},
    )
    assert unknown_claim.status_code == 404


def test_readiness_matches_corrected_claim_checklist():
    result = client.get("/api/claims/CLM-3021").json()["analysis"]
    assert result["readiness_score"] == 40
    assert "Hospital discharge summary submitted" not in result["checklist"]
    assert "Hospital discharge summary submitted" in result["risk_flags"]
    assert calculate_readiness({"id": "test", "product": "Health", "checklist": []}).readiness_score == 0


def test_duplicate_document_event_is_ignored():
    session = "duplicate-event-test"
    first = publish_document_event(session, stage="received", status="completed", message="Received", details="Accepted.")
    duplicate = publish_document_event(session, stage="received", status="completed", message="Received", details="Accepted again.")
    assert duplicate == first
    assert len(get_document_event_store(session)) == 1


def test_supported_image_uses_shared_groq_vision_client(monkeypatch):
    class MockLLM:
        settings = type("Settings", (), {"fast_model": "openai/gpt-oss-20b", "replay": False})()

        async def inspect_image(self, image: bytes, mime_type: str, prompt: str):
            assert mime_type == "image/png"
            return LLMResult(
                content='{"text":"Hospital invoice\\nPatient: Asha Reddy\\nBill amount: Rs. 185000\\nRoom charge Rs. 50000"}',
                provider="groq",
                model="qwen/qwen3.8-27b",
            )

        async def generate_result(self, *args, **kwargs):
            return LLMResult(content="", provider="deterministic", fallback=True)

    image = Image.new("RGB", (20, 20), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    monkeypatch.setattr("backend.app.document_processing.get_llm_client", lambda: MockLLM())
    response = client.post(
        "/api/documents/process",
        data={"session_id": "image-test", "claim_id": "CLM-3021"},
        files={"file": ("invoice.png", output.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["extraction_status"] == "extracted"
    assert response.json()["provider"] == "groq"


def test_complete_patient_pdf_passes_all_validations():
    import os
    pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_documents", "Asha_Reddy_CLM-3021_Complete_Claim_Documents.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    response = client.post(
        "/api/documents/process",
        data={"session_id": "complete-patient-pdf-test", "claim_id": "CLM-3021"},
        files={"file": ("Asha_Reddy_CLM-3021_Complete_Claim_Documents.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True
    assert result["score"] == 100
    assert result["readiness_score"] == 100
    assert result["missing_documents"] == []
    assert result["mismatches"] == []
    assert result["fields_unverified"] == []
    assert result["extracted_fields"]["claimant_name"] == "Asha Reddy"
    assert result["extracted_fields"]["amount"] == "185000"
    assert len(result["checks_passed"]) >= 5

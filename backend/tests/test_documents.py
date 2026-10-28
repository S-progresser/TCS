from backend.app.events import build_document_events, finalize_document_events
from backend.app.orchestrator import validate_document


def test_validate_document_success():
    result = validate_document("invoice.pdf", "Hospital invoice for claim and discharge summary")
    assert result.valid is True
    assert result.score >= 80


def test_validate_document_missing_info():
    result = validate_document("notes.txt", "No invoice or discharge details present")
    assert result.valid is False
    assert any("Invoice or bill not found" in item for item in result.missing_documents)


def test_document_progress_events_round_trip():
    session_id = "document-session-123"
    events = build_document_events(
        session_id=session_id,
        filename="invoice.pdf",
        text="Hospital invoice and discharge summary",
        claim_id="CLM-3021",
    )
    assert any(event["stage"] == "received" for event in events)
    assert any(event["stage"] == "explanation" for event in events)

    final_events = finalize_document_events(
        session_id,
        validate_document("invoice.pdf", "Hospital invoice and discharge summary").model_dump(),
        filename="invoice.pdf",
        claim_id="CLM-3021",
    )
    assert final_events[-1]["type"] == "document.result"
    assert final_events[-1]["result"]["valid"] is True


def test_document_progress_failure_for_unreadable_content():
    events = build_document_events(
        session_id="document-session-456",
        filename="notes.txt",
        text="No invoice or discharge details present",
        claim_id="CLM-3021",
    )
    assert any(event["status"] == "failed" for event in events)

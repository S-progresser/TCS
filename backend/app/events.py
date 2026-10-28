from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from sse_starlette.sse import EventSourceResponse


_DOCUMENT_EVENT_STORE: dict[str, list[dict[str, Any]]] = {}


def event_stream_generator(events: list[dict[str, Any]]):
    for item in events:
        payload = json.dumps(item)
        yield {"event": item.get("type", "message"), "data": payload}


async def document_event_stream(session_id: str) -> Any:
    for _ in range(200):
        if session_id in _DOCUMENT_EVENT_STORE:
            for item in _DOCUMENT_EVENT_STORE[session_id]:
                yield {"event": item.get("type", "message"), "data": json.dumps(item)}
            return
        await asyncio.sleep(0.1)

    fallback = {
        "type": "document.progress",
        "session_id": session_id,
        "stage": "reading",
        "status": "failed",
        "message": "Document analysis unavailable",
        "details": "The backend has no analysis session for this upload yet.",
        "progress": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    yield {"event": "document.progress", "data": json.dumps(fallback)}


def generate_events(*, claim_id: str | None = None, messages: list[str] | None = None):
    entries: list[dict[str, Any]] = []
    for idx, message in enumerate(messages or []):
        entries.append({
            "type": "progress",
            "message": message,
            "progress": int((idx + 1) / max(len(messages or [1]), 1) * 100),
            "claim_id": claim_id,
        })
    return EventSourceResponse(event_stream_generator(entries))


def detect_document_type(filename: str | None) -> str:
    if not filename:
        return "unknown"
    lowered = filename.lower()
    if lowered.endswith((".pdf", ".doc", ".docx")):
        return "document"
    if lowered.endswith((".png", ".jpg", ".jpeg")):
        return "image"
    if lowered.endswith(".txt"):
        return "text"
    return "unknown"


def build_document_events(*, session_id: str | None, filename: str | None, text: str | None = None, claim_id: str | None = None) -> list[dict[str, Any]]:
    doc_type = detect_document_type(filename)
    session_key = session_id or "default"
    events: list[dict[str, Any]] = []
    steps = [
        ("received", "Document received", "The document has been queued for checking.", "completed"),
        ("reading", "Reading document", "Reviewing the uploaded file and extracting any readable text.", "active"),
        ("extracting", "Extracting important details", "Pulling out policy, claim, and billing details that can be checked.", "pending"),
        ("requirements", "Checking insurer requirements", "Comparing the document against the rulebook and insurer requirements.", "pending"),
        ("claim_compare", "Comparing with your claim", "Checking the document against the claim record for mismatches and gaps.", "pending"),
        ("explanation", "Preparing your explanation", "Preparing the final summary and next steps.", "pending"),
    ]

    normalized = (text or "").strip().lower()
    has_negative_document_signal = any(
        phrase in normalized
        for phrase in [
            "no invoice",
            "invoice not",
            "no bill",
            "no discharge",
            "discharge not",
            "discharge summary missing",
            "bill not",
            "missing invoice",
            "missing discharge",
        ]
    )
    has_any_claim_signal = any(word in normalized for word in ["invoice", "bill", "hospital", "claim", "discharge", "policy", "treatment"])
    text_is_meaningful = bool(normalized) and not normalized in {"null", "none", "empty", "n/a"} and (has_any_claim_signal or len(normalized.split()) >= 5)

    for index, (stage, title, detail, status) in enumerate(steps, start=1):
        payload = {
            "type": "document.progress",
            "session_id": session_key,
            "claim_id": claim_id,
            "stage": stage,
            "status": status,
            "message": title,
            "details": detail,
            "progress": int((index / len(steps)) * 100),
            "filename": filename,
            "document_type": doc_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if stage in {"reading", "extracting"} and (not text_is_meaningful or has_negative_document_signal):
            payload["status"] = "failed"
            payload["error"] = "No readable document content was provided."
            payload["details"] = "The uploaded file could not be read or did not contain enough claim-related information to continue."
        events.append(payload)

    for event in events:
        if event["status"] == "failed":
            event["progress"] = 100
            break

    _DOCUMENT_EVENT_STORE[session_key] = events
    return events


def get_document_event_store(session_id: str | None) -> list[dict[str, Any]]:
    session_key = session_id or "default"
    return list(_DOCUMENT_EVENT_STORE.get(session_key, []))


def finalize_document_events(session_id: str | None, result: dict[str, Any], *, filename: str | None, claim_id: str | None = None) -> list[dict[str, Any]]:
    session_key = session_id or "default"
    events = get_document_event_store(session_key)
    if not events:
        events = build_document_events(session_id=session_key, filename=filename, text=None, claim_id=claim_id)

    final_progress = {
        "type": "document.result",
        "session_id": session_key,
        "claim_id": claim_id,
        "stage": "explanation",
        "status": "completed",
        "message": "Final explanation ready",
        "details": "The document review summary and next actions are ready to display.",
        "progress": 100,
        "filename": filename,
        "document_type": detect_document_type(filename),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    events = [*events[:-1], {**events[-1], "status": "completed", "progress": 100, "message": "Preparing your explanation"}, final_progress]
    _DOCUMENT_EVENT_STORE[session_key] = events
    return events

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from sse_starlette.sse import EventSourceResponse


_DOCUMENT_EVENT_STORE: dict[str, list[dict[str, Any]]] = {}
_DOCUMENT_EVENT_DONE: set[str] = set()


def event_stream_generator(events: list[dict[str, Any]]):
    for item in events:
        payload = json.dumps(item)
        yield {"event": item.get("type", "message"), "data": payload}


async def document_event_stream(session_id: str) -> Any:
    cursor = 0
    for _ in range(1200):
        events = _DOCUMENT_EVENT_STORE.get(session_id, [])
        while cursor < len(events):
            item = events[cursor]
            cursor += 1
            yield {"event": item.get("type", "message"), "data": json.dumps(item)}
            if item.get("type") in {"document.completed", "document.failed"}:
                return
        if session_id in _DOCUMENT_EVENT_DONE:
            return
        await asyncio.sleep(0.1)

    publish_document_event(
        session_id,
        stage="reading",
        status="failed",
        message="Document analysis timed out",
        details="The document processing session did not finish in time.",
        event_type="document.failed",
        error="analysis_timeout",
    )
    item = _DOCUMENT_EVENT_STORE[session_id][-1]
    yield {"event": item["type"], "data": json.dumps(item)}


def publish_document_event(
    session_id: str,
    *,
    stage: str,
    status: str,
    message: str,
    details: str,
    claim_id: str | None = None,
    filename: str | None = None,
    document_type: str | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    event_type: str = "document.progress",
) -> dict[str, Any]:
    event = {
        "type": event_type,
        "session_id": session_id,
        "claim_id": claim_id,
        "stage": stage,
        "status": status,
        "message": message,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if filename is not None:
        event["filename"] = filename
    if document_type is not None:
        event["document_type"] = document_type
    if result is not None:
        event["result"] = result
    if error is not None:
        event["error"] = error
    existing = _DOCUMENT_EVENT_STORE.setdefault(session_id, [])
    duplicate = next(
        (
            previous for previous in existing
            if previous.get("type") == event_type
            and previous.get("stage") == stage
            and previous.get("status") == status
            and previous.get("message") == message
        ),
        None,
    )
    if duplicate is not None:
        return duplicate
    existing.append(event)
    if len(_DOCUMENT_EVENT_STORE) > 100:
        oldest = next(iter(_DOCUMENT_EVENT_STORE))
        if oldest != session_id:
            _DOCUMENT_EVENT_STORE.pop(oldest, None)
            _DOCUMENT_EVENT_DONE.discard(oldest)
    if event_type in {"document.completed", "document.failed"}:
        _DOCUMENT_EVENT_DONE.add(session_id)
    return event


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


def get_document_event_store(session_id: str | None) -> list[dict[str, Any]]:
    session_key = session_id or "default"
    return list(_DOCUMENT_EVENT_STORE.get(session_key, []))

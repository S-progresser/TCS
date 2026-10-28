from __future__ import annotations

from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from backend.app.events import build_document_events, document_event_stream, finalize_document_events, generate_events, get_document_event_store
from backend.app.orchestrator import answer_query, calculate_readiness, get_claim_by_id, validate_document
from backend.app.retriever import load_claims, load_rulebooks
from backend.app.schemas import QueryRequest

app = FastAPI(title="ClaimSense API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "claimsense"}


@app.get("/api/claims")
def list_claims() -> list[dict[str, Any]]:
    return load_claims()


@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: str) -> dict[str, Any]:
    claim = get_claim_by_id(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    claim["analysis"] = calculate_readiness(claim).model_dump()
    return claim


@app.get("/api/rulebooks")
def list_rulebooks() -> list[dict[str, Any]]:
    return [rule.model_dump() for rule in load_rulebooks()]


@app.post("/api/query")
async def handle_query(payload: QueryRequest):
    try:
        return (await answer_query(payload.claim_id, payload.question, payload.language, payload.document_context)).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/documents/process")
async def process_document(
    file: UploadFile | None = File(default=None),
    filename: str = Form("document.pdf"),
    context: str = Form(""),
    session_id: str = Form(""),
    claim_id: str = Form(""),
):
    text = None
    if file is not None:
        payload = await file.read()
        text = payload.decode("utf-8", errors="ignore")

    doc_session = session_id or "document-session"
    result = validate_document(filename or "document.pdf", text or context)
    events = build_document_events(session_id=doc_session, filename=filename or "document.pdf", text=text or context, claim_id=claim_id or None)
    for event in events:
        if event["status"] == "failed":
            event["status"] = "failed"
    finalize_document_events(doc_session, result.model_dump(), filename=filename or "document.pdf", claim_id=claim_id or None)
    return result.model_dump()


@app.get("/api/documents/stream")
async def stream_document_progress(session_id: str):
    return EventSourceResponse(document_event_stream(session_id))


@app.get("/api/replay")
def replay_demo() -> dict[str, Any]:
    return {
        "mode": "replay",
        "steps": [
            "Load claim CLM-3021 and show status timeline",
            "Explain document gaps and expected settlement",
            "Highlight the next-action checklist and hospital follow-up",
        ],
    }


@app.get("/api/chat/stream")
async def stream_claim_progress(claim_id: str = "CLM-3021"):
    messages = [
        "Reviewing claim documents",
        "Checking policy coverage and deductions",
        "Summarizing next action for the customer",
    ]
    return generate_events(claim_id=claim_id, messages=messages)

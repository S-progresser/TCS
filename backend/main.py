from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from backend.app.document_processing import MAX_UPLOAD_BYTES, analyze_upload, detected_content_type, safe_filename
from backend.app.events import document_event_stream, generate_events, publish_document_event
from backend.app.llm import get_llm_client
from backend.app.orchestrator import answer_query, calculate_readiness, get_claim_by_id
from backend.app.retriever import load_claims, load_rulebooks
from backend.app.schemas import QueryRequest

app = FastAPI(title="ClaimSense API", version="0.1.0")
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "claimsense", **get_llm_client().status()}


@app.get("/api/health/groq")
async def check_groq_connection() -> dict[str, Any]:
    return await get_llm_client().check_connection()


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
    if not session_id or len(session_id) > 128:
        raise HTTPException(status_code=422, detail="A valid analysis session_id is required.")
    if not claim_id:
        raise HTTPException(status_code=422, detail="Select a claim before uploading a document.")
    claim = get_claim_by_id(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found.")
    if file is None:
        raise HTTPException(status_code=422, detail="Upload a PDF, JPG, JPEG, or PNG file.")

    upload_name = safe_filename(file.filename or filename)
    try:
        payload = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()
    if len(payload) > MAX_UPLOAD_BYTES:
        publish_document_event(
            session_id,
            stage="received",
            status="failed",
            message="File is too large",
            details="The maximum upload size is 10 MB.",
            claim_id=claim_id,
            filename=upload_name,
            event_type="document.failed",
            error="file_too_large",
        )
        raise HTTPException(status_code=413, detail="The maximum upload size is 10 MB.")
    try:
        mime_type, content_kind = detected_content_type(upload_name, payload)
    except ValueError as exc:
        publish_document_event(
            session_id,
            stage="received",
            status="failed",
            message="Unsupported or invalid file",
            details=str(exc),
            claim_id=claim_id,
            filename=upload_name,
            event_type="document.failed",
            error="unsupported_file",
        )
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    async def emit(**event: Any) -> None:
        publish_document_event(
            session_id,
            claim_id=claim_id,
            filename=upload_name,
            **event,
        )

    try:
        result = await analyze_upload(
            filename=upload_name,
            content=payload,
            mime_type=mime_type,
            content_kind=content_kind,
            claim=claim,
            on_stage=emit,
        )
    except Exception as exc:
        logger.exception("Document analysis failed for claim %s", claim_id)
        publish_document_event(
            session_id,
            stage="explanation",
            status="failed",
            message="Document analysis failed",
            details="The uploaded document could not be analyzed. Please retry with a supported file.",
            claim_id=claim_id,
            filename=upload_name,
            event_type="document.failed",
            error="analysis_failed",
        )
        raise HTTPException(status_code=500, detail="Document analysis failed. Please retry with a supported file.") from exc
    return result.model_dump()


@app.get("/api/documents/stream")
async def stream_document_progress(session_id: str):
    if not session_id or len(session_id) > 128:
        raise HTTPException(status_code=422, detail="A valid analysis session_id is required.")
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

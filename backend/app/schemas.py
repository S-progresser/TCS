from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ClaimSummary(BaseModel):
    id: str
    customer_name: str
    policy_number: str
    product: str
    claim_type: str
    status: str
    claim_amount: float
    insurer: str
    branch: str
    summary: str


class PolicyRule(BaseModel):
    id: str
    title: str
    category: str
    source: str
    summary: str
    keywords: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    itemization_required: bool = False
    signature_required: bool = False


class KnowledgeChunk(BaseModel):
    id: str
    title: str
    text: str
    source: str
    tags: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    title: str
    snippet: str
    source: str
    score: float


class QueryRequest(BaseModel):
    claim_id: str
    question: str
    language: Literal["en", "hi", "kn"] = "en"
    document_context: str | None = None


class ConciergePlanOutput(BaseModel):
    language: Literal["en", "hi", "kn"]
    intent: Literal["document_review", "coverage_check", "claim_status", "general_claim_help"]
    tone: Literal["neutral", "urgent", "frustrated"]
    normalized_query: str
    needs_document_analysis: bool


class DocumentReview(BaseModel):
    filename: str
    valid: bool
    score: int | None
    missing_documents: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    fields_missing: list[str] = Field(default_factory=list)
    fields_unverified: list[str] = Field(default_factory=list)
    provider_message: str | None = None
    claim_id: str | None = None
    extraction_status: Literal["extracted", "unreadable", "unsupported"] = "extracted"
    extraction_message: str | None = None
    extracted_fields: dict[str, str] = Field(default_factory=dict)
    checks_passed: list[str] = Field(default_factory=list)
    readiness_score: int | None = None
    replayed: bool = False
    provider: str = "deterministic"
    extracted_document_type: str | None = None


class ClaimAnalysis(BaseModel):
    claim_id: str
    readiness_score: int
    status: str
    summary: str
    checklist: list[str]
    next_steps: list[str]
    deductible: float
    copay: float
    estimated_payout: float
    risk_flags: list[str]


class QueryResponse(BaseModel):
    claim_id: str
    answer: str
    citations: list[str]
    language: str
    next_actions: list[str]
    confidence: float
    provider: str = "deterministic"


class StreamEvent(BaseModel):
    type: str
    message: str
    progress: int | None = None
    claim_id: str | None = None
    session_id: str | None = None
    stage: str | None = None
    status: Literal["pending", "active", "completed", "failed"] | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    filename: str | None = None
    document_type: str | None = None
    details: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def normalize_query(question: str) -> str:
    return " ".join((question or "").lower().replace("\n", " ").replace("-", " ").split())


def detect_language(question: str) -> str:
    lowered = normalize_query(question)
    if any(token in lowered for token in ["हिंदी", "दावा", "दस्तावेज़", "कृपया", "नमस्ते"]):
        return "hi"
    if any(token in lowered for token in ["ಕನ್ನಡ", "ದಾವೆ", "ದಾಖಲೆ", "ನಮಸ್ಕಾರ", "ಪರಿಶೀಲನೆ"]):
        return "kn"
    return "en"


def detect_intent(question: str) -> str:
    lowered = normalize_query(question)
    document_tokens = [
        "missing", "document", "invoice", "bill", "discharge", "upload", "submit",
        "submission", "paperwork", "required document", "what do i need", "provide",
        "दस्तावेज़", "बिल", "डिस्चार्ज", "दावा", "अपलोड", "कमी", "दर्ज़", "दाखला"
    ]
    coverage_tokens = ["coverage", "policy", "deductible", "claim amount", "benefit", "पॉलिसी", "कवर"]
    status_tokens = ["status", "progress", "where is", "update", "स्थिति", "प्रगति", "अपडेट"]
    if any(token in lowered for token in document_tokens):
        return "document_review"
    if any(token in lowered for token in coverage_tokens):
        return "coverage_check"
    if any(token in lowered for token in status_tokens):
        return "claim_status"
    return "general_claim_help"


def infer_claim_id(question: str, fallback: str | None = None) -> str | None:
    import re

    match = re.search(r"CLM-\d+", question, flags=re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return fallback


def detect_tone(question: str) -> str:
    lowered = normalize_query(question)
    if any(token in lowered for token in ["urgent", "asap", "immediately", "very urgent"]):
        return "urgent"
    if any(token in lowered for token in ["frustrated", "angry", "annoyed", "please help me"]):
        return "frustrated"
    return "neutral"


@dataclass
class ExecutionPlan:
    language: str
    intent: str
    claim_id: str | None
    tone: str
    normalized_query: str
    needs_document_analysis: bool
    execution_steps: list[str] = field(default_factory=list)


def build_concierge_plan(question: str, *, claim_id: str | None = None) -> ExecutionPlan:
    normalized = normalize_query(question)
    resolved_claim_id = infer_claim_id(question, claim_id)
    language = detect_language(question)
    intent = detect_intent(question)
    tone = detect_tone(question)
    document_indicators = [
        "document", "invoice", "bill", "discharge", "upload", "missing", "submit",
        "submission", "paperwork", "required document", "what do i need", "provide",
        "दस्तावेज़", "बिल", "डिस्चार्ज", "दाखला", "अपलोड", "कमी", "दर्ज़",
    ]
    needs_document_analysis = any(token in normalized for token in document_indicators)

    steps = [
        "Review the request and customer intent",
        "Retrieve the relevant claim and policy context",
    ]
    if needs_document_analysis:
        steps.append("Run document validation and gap detection")
    steps.append("Prepare a verified explanation for the customer")

    return ExecutionPlan(
        language=language,
        intent=intent,
        claim_id=resolved_claim_id,
        tone=tone,
        normalized_query=normalized,
        needs_document_analysis=needs_document_analysis,
        execution_steps=steps,
    )


def calculate_deductible_and_payout(claim: dict[str, Any]) -> dict[str, float]:
    deductible = float(claim.get("deductible", 0) or 0)
    copay = float(claim.get("copay", 0) or 0)
    claim_amount = float(claim.get("claim_amount", 0) or 0)
    estimated_payout = max(0.0, claim_amount - deductible - copay)
    return {
        "deductible": deductible,
        "copay": copay,
        "estimated_payout": estimated_payout,
    }


def has_document_gap(document_text: str | None) -> bool:
    normalized = (document_text or "").strip().lower()
    if not normalized:
        return False
    negative_phrases = [
        "no invoice", "invoice not", "missing invoice", "no bill", "bill not", "missing bill",
        "no discharge", "discharge not", "discharge summary missing", "missing discharge",
    ]
    if any(phrase in normalized for phrase in negative_phrases):
        return True

    discharge_has_summary = "discharge" in normalized and any(token in normalized for token in ["summary", "report", "letter", "certificate"])
    if "discharge" in normalized and not discharge_has_summary and ("details" in normalized or "present" in normalized):
        return True
    return False


def compare_name_date_amount(claim: dict[str, Any], text: str | None) -> list[str]:
    mismatches: list[str] = []
    normalized = (text or "").lower()
    if claim.get("customer_name") and claim["customer_name"].lower() not in normalized and "patient" not in normalized and "member" not in normalized:
        mismatches.append("Customer name could not be matched to the uploaded document.")
    if claim.get("treatment_date") and claim["treatment_date"] not in normalized and claim.get("date_of_service") and claim["date_of_service"] not in normalized:
        mismatches.append("Treatment date could not be verified in the uploaded document.")
    if claim.get("claim_amount") and str(claim["claim_amount"]) not in normalized:
        mismatches.append("Claim amount could not be verified in the uploaded document.")
    return mismatches


def escalation_rules(claim: dict[str, Any], *, missing_documents: list[str] | None = None, mismatches: list[str] | None = None) -> str | None:
    missing = missing_documents or []
    mismatches_list = mismatches or []
    if any("invoice" in item.lower() or "bill" in item.lower() for item in missing):
        return "Escalate to the hospital billing desk for original invoice documentation."
    if any("discharge" in item.lower() for item in missing):
        return "Escalate to the hospital discharge desk for the signed discharge summary."
    if mismatches_list:
        return "Escalate to the claim analyst for a manual document-to-claim comparison."
    return None


def validate_request_schema(payload: dict[str, Any]) -> bool:
    required = ["claim_id", "question"]
    return all(key in payload for key in required) and bool(str(payload.get("question") or "").strip())

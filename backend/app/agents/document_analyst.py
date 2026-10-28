from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.deterministic import compare_name_date_amount, escalation_rules, has_document_gap


@dataclass
class DocumentAnalysisResult:
    filename: str
    valid: bool
    score: int
    missing_documents: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    fields_missing: list[str] = field(default_factory=list)
    fields_unverified: list[str] = field(default_factory=list)
    provider_message: str | None = None


class DocumentAnalyst:
    async def analyze(self, *, filename: str, text: str | None, claim: dict[str, Any] | None = None) -> DocumentAnalysisResult:
        from backend.app.orchestrator import validate_document

        base_result = validate_document(filename, text)
        mismatches = list(base_result.mismatches)
        fields_missing = list(base_result.missing_documents)
        fields_unverified: list[str] = []

        if claim:
            mismatches.extend(compare_name_date_amount(claim, text))
            if any("date" in item.lower() for item in mismatches):
                fields_unverified.append("Treatment date")
            if any("amount" in item.lower() for item in mismatches):
                fields_unverified.append("Claim amount")
            if any("name" in item.lower() for item in mismatches):
                fields_unverified.append("Customer name")

        if has_document_gap(text):
            fields_missing.append("Missing required document evidence")
            if not any("Discharge summary missing" in item for item in base_result.missing_documents):
                base_result.missing_documents.append("Discharge summary missing")

        next_steps = list(base_result.next_steps)
        escalation_note = escalation_rules(claim or {}, missing_documents=base_result.missing_documents, mismatches=mismatches)
        if escalation_note:
            next_steps.append(escalation_note)

        return DocumentAnalysisResult(
            filename=base_result.filename,
            valid=base_result.valid,
            score=base_result.score,
            missing_documents=list(dict.fromkeys(base_result.missing_documents)),
            mismatches=list(dict.fromkeys(mismatches)),
            next_steps=next_steps,
            fields_missing=list(dict.fromkeys(fields_missing)),
            fields_unverified=list(dict.fromkeys(fields_unverified)),
            provider_message=escalation_note,
        )

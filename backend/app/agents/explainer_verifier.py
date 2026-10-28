from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.deterministic import detect_language
from backend.app.schemas import QueryResponse


@dataclass
class VerificationResult:
    answer: str
    citations: list[str]
    language: str
    next_actions: list[str]
    confidence: float
    verified: bool
    provider_message: str | None = None


class ExplainerVerifier:
    async def compose(
        self,
        *,
        claim: dict[str, Any],
        investigation: Any,
        document_review: Any | None = None,
        plan: Any | None = None,
        fallback_answer: str | None = None,
    ) -> QueryResponse:
        language = plan.language if plan is not None else detect_language(fallback_answer or claim.get("summary", ""))
        guidance = investigation.evidence if investigation else []
        citations = investigation.citations if investigation else []
        verified = bool(citations)

        if document_review is not None:
            if document_review.missing_documents:
                verified = verified and not bool(document_review.missing_documents)
            if document_review.mismatches:
                verified = False

        base = fallback_answer or (
            f"Your claim {claim.get('id', 'unknown')} is currently in {claim.get('status', 'review')} status. "
            "The next required action is to upload or verify the missing document details before the insurer can finalize the decision."
        )
        if guidance:
            base = f"{base} {guidance[0]}"

        next_actions = [
            "Upload missing documents if required",
            "Confirm treatment dates and claim amount",
            "Check the insurer's next step with the provider",
        ]
        if document_review is not None and document_review.next_steps:
            next_actions = document_review.next_steps[:3]

        if not citations:
            citations = ["Internal claims policy", "IRDAI claim guidance"]

        if not verified:
            base = (
                f"I cannot confirm a successful verification for claim {claim.get('id', 'unknown')} because the evidence is incomplete or unsupported. "
                "Please complete the required documents and claim details before confirming settlement."
            )
            next_actions = [
                "Upload the required invoice and discharge summary",
                "Confirm the policy number and treatment dates",
                "Request a manual verification from the insurer",
            ]

        if language == "hi":
            base = "दावा अभी दस्तावेज़ सत्यापन में है। अंतिम बिल और डिस्चार्ज सारांश की पुष्टि करें।"
        elif language == "kn":
            base = "ಹಣ दावा ಇನ್ನೂ ದಾಖಲೆ ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ. ಅಂತಿಮ ಬಿಲ್ ಮತ್ತು ಡಿಸ್ಚಾರ್ಜ್ ವರದಿಯನ್ನು ಪರಿಶೀಲಿಸಿ."

        provider_message = None
        if document_review and document_review.provider_message:
            provider_message = document_review.provider_message

        return QueryResponse(
            claim_id=str(claim.get('id', 'unknown')),
            answer=base,
            citations=citations,
            language=language,
            next_actions=next_actions,
            confidence=0.88 if verified else 0.58,
        )

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from backend.app.deterministic import detect_language
from backend.app.llm import get_llm_client
from backend.app.schemas import QueryResponse
from pydantic import ValidationError


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
        question = plan.normalized_query if plan is not None else ""
        intent = plan.intent if plan is not None else "general_claim_help"
        analysis = claim.get("analysis", {})
        pending_items = list(analysis.get("risk_flags", []))
        next_actions = [f"Submit: {item.rstrip('.')}" for item in pending_items]
        if not next_actions:
            next_actions = list(analysis.get("next_steps", []))
        if document_review is not None and getattr(document_review, "next_steps", None):
            next_actions = document_review.next_steps[:3]
        if not next_actions:
            next_actions = ["Contact the insurer for the next required step."]

        # Construct a grounded base answer addressing the question directly
        lowered_q = question.lower()
        if any(term in lowered_q for term in ["why", "invoice", "bill", "discharge", "receipt"]):
            if any(term in lowered_q for term in ["invoice", "bill"]):
                base = (
                    f"For claim {claim.get('id', 'unknown')}, the final hospital invoice is required to verify "
                    f"the billed medical charges against eligible policy benefits before settlement can proceed. "
                    f"It is currently listed as an outstanding checklist item."
                )
            elif any(term in lowered_q for term in ["discharge"]):
                base = (
                    f"For claim {claim.get('id', 'unknown')}, the hospital discharge summary is required to confirm "
                    f"admission dates, diagnosis, and treatment details. It is currently listed as an outstanding checklist item."
                )
            elif pending_items:
                base = (
                    f"For claim {claim.get('id', 'unknown')}, the checklist shows these items are still required "
                    f"to substantiate your claim: {'; '.join(pending_items)}."
                )
            else:
                base = f"For claim {claim.get('id', 'unknown')}, all standard checklist items are marked complete."
        elif any(term in lowered_q for term in ["what documents", "submit next", "need next", "what do i need", "what next", "next steps"]):
            if pending_items:
                requirements = "; ".join(pending_items)
                base = (
                    f"For claim {claim.get('id', 'unknown')}, the selected claim checklist still shows these "
                    f"items as outstanding: {requirements}. Submit them for review. These demo requirements "
                    "do not guarantee claim approval."
                )
            else:
                base = (
                    f"For claim {claim.get('id', 'unknown')}, the selected claim checklist shows no outstanding "
                    "document items. Confirm any additional requirements with the insurer."
                )
        elif any(term in lowered_q for term in ["status", "progress", "update", "where is"]) or intent == "claim_status":
            base = fallback_answer or (
                f"Your claim {claim.get('id', 'unknown')} is currently in '{claim.get('status', 'under review')}' status. "
                f"{claim.get('summary', 'Claim is undergoing review.')}"
            )
        elif intent == "document_review":
            if pending_items:
                requirements = "; ".join(pending_items)
                base = (
                    f"For claim {claim.get('id', 'unknown')}, the selected claim checklist still shows these "
                    f"items as outstanding: {requirements}. Submit them for review. These demo requirements "
                    "do not guarantee claim approval."
                )
            else:
                base = (
                    f"For claim {claim.get('id', 'unknown')}, the selected claim checklist shows no outstanding "
                    "document items. Confirm any additional requirements with the insurer."
                )
        elif intent == "coverage_check":
            base = (
                f"Claim {claim.get('id', 'unknown')} is a {claim.get('product', 'insurance')} claim "
                f"currently marked {claim.get('status', 'under review')}. The claim record lists an amount "
                f"of ₹{claim.get('claim_amount', 0):,.0f}; coverage and payable amount depend on policy review."
            )
        elif fallback_answer:
            base = fallback_answer
        else:
            base = str(claim.get("summary") or f"Claim {claim.get('id', 'unknown')} is currently {claim.get('status', 'under review')}.")

        if document_review is not None and (getattr(document_review, "missing_documents", None) or getattr(document_review, "mismatches", None)):
            if intent == "document_review" and pending_items:
                base += " The uploaded document also has confirmed gaps that need review."
            else:
                base = (
                    f"I cannot confirm a successful document verification for claim {claim.get('id', 'unknown')}. "
                    f"The claim is currently {claim.get('status', 'under review')}; the listed document gaps need review."
                )

        if language == "hi":
            base = f"आपका दावा {claim.get('id', 'unknown')} अभी {claim.get('status', 'समीक्षा')} स्थिति में है।"
        elif language == "kn":
            base = f"ನಿಮ್ಮ ಕ್ಲೇಮ್ {claim.get('id', 'unknown')} ಪ್ರಸ್ತುತ {claim.get('status', 'ಪರಿಶೀಲನೆ')} ಸ್ಥಿತಿಯಲ್ಲಿದೆ."

        response = QueryResponse(
            claim_id=str(claim.get("id", "unknown")),
            answer=base,
            citations=citations,
            language=language,
            next_actions=next_actions,
            confidence=0.58 if document_review and (getattr(document_review, "missing_documents", None) or getattr(document_review, "mismatches", None)) else 0.7,
            provider="deterministic",
        )

        llm = get_llm_client()
        doc_findings = None
        if document_review is not None:
            if hasattr(document_review, "model_dump"):
                doc_findings = document_review.model_dump()
            else:
                doc_findings = {
                    "filename": getattr(document_review, "filename", None),
                    "missing_documents": getattr(document_review, "missing_documents", []),
                    "mismatches": getattr(document_review, "mismatches", []),
                }

        prompt = json.dumps({
            "task": (
                "Answer the customer's actual question directly in plain, concise language. "
                "Ground your answer strictly in the provided claim details, pending checklist items, and document findings. "
                "Never invent policy rules, medical facts, or guaranteed payouts. "
                "Output ONLY a JSON object with keys: 'answer' (string direct answer), 'next_actions' (list of strings), 'citations' (list of strings from allowed_citations)."
            ),
            "customer_question": question,
            "intent": intent,
            "claim": {
                key: claim.get(key)
                for key in ("id", "customer_name", "policy_number", "product", "claim_type", "status", "claim_amount", "summary", "deductible", "copay")
            },
            "pending_requirements": pending_items,
            "checklist_completed": analysis.get("checklist", []),
            "checklist_pending": pending_items,
            "retrieved_evidence": guidance,
            "allowed_citations": citations,
            "document_findings": doc_findings,
            "allowed_actions": next_actions,
            "language": language,
            "fallback": json.dumps(response.model_dump()),
        })

        selected_model = getattr(llm.settings, "fast_model", getattr(llm.settings, "smart_model", None))
        completion = await llm.generate_result(prompt, model=selected_model, json_mode=True, max_tokens=450)

        # Clear error handling: do not silently return generic status when generation fails
        if completion.error and completion.error in ("timeout", "rate_limited"):
            error_code = completion.error
            if error_code == "timeout":
                response.answer = f"The AI assistant timed out while processing your question for claim {claim.get('id')}. Verified record shows status is '{claim.get('status')}'. Please retry in a moment."
            elif error_code == "rate_limited":
                response.answer = f"The AI assistant is temporarily rate-limited. Verified record shows claim {claim.get('id')} is currently '{claim.get('status')}'. Please retry shortly."
            response.provider = completion.provider
            return response

        if completion.provider in ("groq", "gemini") and completion.content:
            raw_text = completion.content.strip()
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(1)
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    ans = parsed.get("answer") or parsed.get("explanation")
                    if ans and isinstance(ans, str) and len(ans.strip()) > 5:
                        supported_numbers = {
                            str(value)
                            for value in (claim.get("claim_amount"), claim.get("deductible"), claim.get("copay"))
                            if value is not None
                        }
                        unsupported_numbers = [
                            number for number in re.findall(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?", ans)
                            if len(number.replace(",", "")) >= 4 and number.replace(",", "") not in {
                                item.replace(",", "") for item in supported_numbers
                            } and number not in str(claim.get("id", ""))
                        ]
                        if not unsupported_numbers:
                            response.answer = ans.strip()
                            if parsed.get("next_actions") and isinstance(parsed["next_actions"], list):
                                valid_actions = [str(a) for a in parsed["next_actions"] if a]
                                if valid_actions:
                                    response.next_actions = valid_actions[:5]
                            if parsed.get("citations") and isinstance(parsed["citations"], list):
                                response.citations = [str(c) for c in parsed["citations"] if str(c) in citations]
                            response.provider = completion.provider
                            return response
            except (json.JSONDecodeError, TypeError):
                pass

        return response

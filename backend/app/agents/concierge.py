from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from backend.app.deterministic import ExecutionPlan, build_concierge_plan
from backend.app.llm import get_llm_client
from backend.app.schemas import ConciergePlanOutput
import json


@dataclass
class ConciergeResult:
    plan: ExecutionPlan


class ConciergeAgent:
    def plan(self, question: str, *, claim_id: str | None = None, document_context: str | None = None) -> ConciergeResult:
        plan = build_concierge_plan(question, claim_id=claim_id)
        if document_context and any(word in (document_context or "").lower() for word in ["invoice", "bill", "discharge", "claim"]):
            plan.needs_document_analysis = True
        return ConciergeResult(plan=plan)

    async def understand(self, question: str, *, claim_id: str | None = None, document_context: str | None = None) -> ConciergeResult:
        result = self.plan(question, claim_id=claim_id, document_context=document_context)
        plan = result.plan
        if plan.intent != "general_claim_help":
            return result
        llm = get_llm_client()
        prompt = json.dumps({
            "task": "Classify the customer request. Return only JSON matching the given schema.",
            "message": question[:2000],
            "schema": {
                "language": "en|hi|kn",
                "intent": "document_review|coverage_check|claim_status|general_claim_help",
                "tone": "neutral|urgent|frustrated",
                "normalized_query": "short retrieval query",
                "needs_document_analysis": "boolean",
            },
            "fallback": "",
        })
        completion = await llm.generate_result(prompt, model=llm.settings.fast_model, json_mode=True, max_tokens=180)
        if completion.provider != "groq":
            return result
        try:
            parsed = ConciergePlanOutput.model_validate_json(completion.content)
        except ValidationError:
            return result
        plan.language = parsed.language
        plan.intent = parsed.intent
        plan.tone = parsed.tone
        plan.normalized_query = parsed.normalized_query[:300] or plan.normalized_query
        plan.needs_document_analysis = parsed.needs_document_analysis
        return result

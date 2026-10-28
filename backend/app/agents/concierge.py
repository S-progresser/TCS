from __future__ import annotations

from dataclasses import dataclass

from backend.app.deterministic import ExecutionPlan, build_concierge_plan


@dataclass
class ConciergeResult:
    plan: ExecutionPlan


class ConciergeAgent:
    def plan(self, question: str, *, claim_id: str | None = None, document_context: str | None = None) -> ConciergeResult:
        plan = build_concierge_plan(question, claim_id=claim_id)
        if document_context and any(word in (document_context or "").lower() for word in ["invoice", "bill", "discharge", "claim"]):
            plan.needs_document_analysis = True
        return ConciergeResult(plan=plan)

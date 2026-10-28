from __future__ import annotations

from typing import Any

from openai import OpenAI

from backend.app.config import get_settings


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client: OpenAI | None = None
        if settings.groq_api_key:
            self.client = OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")
        elif settings.openrouter_api_key:
            self.client = OpenAI(api_key=settings.openrouter_api_key, base_url="https://openrouter.ai/api/v1")

    async def generate(self, prompt: str, *, model: str | None = None, max_tokens: int = 350) -> str:
        if not self.client:
            return self._deterministic_reply(prompt)

        try:
            response = self.client.chat.completions.create(
                model=model or self.settings.fast_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or self._deterministic_reply(prompt)
        except Exception:
            return self._deterministic_reply(prompt)

    def _deterministic_reply(self, prompt: str) -> str:
        lowered = prompt.lower()
        if "status" in lowered:
            return "The claim is currently in the documentation review stage. The insurer is awaiting a final hospital discharge summary and invoice copy before settlement approval."
        if "coverage" in lowered or "deductible" in lowered:
            return "The policy covers hospitalization for eligible in-network treatment, subject to the deductible and co-pay conditions. The expected deductible is 10% of the approved amount, capped at the policy limit."
        if "document" in lowered or "missing" in lowered:
            return "We are missing a final discharge summary and the original invoice. Please share these two documents to avoid a delay in claim approval."
        if "next" in lowered or "action" in lowered:
            return "Next step: upload the remaining documents, confirm the treatment dates, and ask the hospital for the discharge summary."
        return "The claim is progressing under standard review. Please upload the missing documents and confirm the final bill to continue with the settlement process."

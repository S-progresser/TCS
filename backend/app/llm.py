from __future__ import annotations

import asyncio
import base64
import email.utils
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from backend.app.config import get_settings

LLM_CALL_TIMEOUT_SECONDS = 15


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str | None = None
    error: str | None = None
    fallback: bool = False


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client: OpenAI | None = None
        self.gemini_client: Any = None
        if settings.gemini_api_key and not settings.replay:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=settings.gemini_api_key)
            except Exception:
                self.gemini_client = None
        if settings.groq_api_key and not settings.replay:
            self.client = OpenAI(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                timeout=12.0,
                max_retries=0,
            )
        self.last_error: str | None = None

    async def generate(self, prompt: str, *, model: str | None = None, max_tokens: int = 350) -> str:
        result = await self.generate_result(prompt, model=model, max_tokens=max_tokens)
        return result.content

    async def generate_result(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 350,
        json_mode: bool = False,
    ) -> LLMResult:
        selected_model = model or self.settings.fast_model
        # 1. Try Gemini if configured
        gemini = getattr(self, "gemini_client", None)
        if gemini is not None:
            try:
                gemini_model = getattr(self.settings, "gemini_model", "gemini-2.5-flash")
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        gemini.models.generate_content,
                        model=gemini_model,
                        contents=prompt,
                    ),
                    timeout=LLM_CALL_TIMEOUT_SECONDS,
                )
                content = getattr(response, "text", None) or ""
                if not content:
                    raise ValueError("Gemini returned an empty response")
                self.last_error = None
                return LLMResult(content=content, provider="gemini", model=gemini_model)
            except Exception as exc:
                error = self._error_code(exc)
                self.last_error = error
                if self.client is None:
                    provider = "replay" if getattr(self.settings, "replay", False) else "deterministic"
                    return LLMResult(
                        content=self._deterministic_reply(prompt),
                        provider=provider,
                        model=None,
                        error=error,
                        fallback=True,
                    )

        # 2. Try Groq if configured
        if self.client is None:
            provider = "replay" if getattr(self.settings, "replay", False) else "deterministic"
            return LLMResult(
                content=self._deterministic_reply(prompt),
                provider=provider,
                model=None,
                fallback=True,
                error="GROQ_API_KEY is not configured",
            )
        try:
            messages = [{"role": "user", "content": prompt}]
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._complete,
                    messages,
                    selected_model,
                    max_tokens,
                    json_mode,
                ),
                timeout=LLM_CALL_TIMEOUT_SECONDS,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Groq returned an empty response")
            self.last_error = None
            return LLMResult(content=content, provider="groq", model=selected_model)
        except (RateLimitError, APITimeoutError, APIConnectionError, APIStatusError, TimeoutError, ValueError) as exc:
            error = self._error_code(exc)
            self.last_error = error
            provider = "replay" if getattr(self.settings, "replay", False) else "deterministic"
            return LLMResult(
                content=self._deterministic_reply(prompt),
                provider=provider,
                model=None,
                error=error,
                fallback=True,
            )

    async def inspect_image(self, image: bytes, mime_type: str, prompt: str) -> LLMResult:
        if self.client is None:
            provider = "replay" if self.settings.replay else "deterministic"
            return LLMResult(
                content="",
                provider=provider,
                error="GROQ_API_KEY is not configured",
                fallback=True,
            )
        data_url = f"data:{mime_type};base64,{base64.b64encode(image).decode('ascii')}"
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._complete,
                    [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }],
                    self.settings.vision_model,
                    600,
                    True,
                ),
                timeout=LLM_CALL_TIMEOUT_SECONDS,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Groq returned an empty response")
            self.last_error = None
            return LLMResult(content=content, provider="groq", model=self.settings.vision_model)
        except (RateLimitError, APITimeoutError, APIConnectionError, APIStatusError, TimeoutError, ValueError) as exc:
            error = self._error_code(exc)
            self.last_error = error
            provider = "replay" if self.settings.replay else "deterministic"
            return LLMResult(content="", provider=provider, error=error, fallback=True)

    def _complete(self, messages: list[dict[str, Any]], model: str, max_tokens: int, json_mode: bool):
        if self.client is None:
            raise RuntimeError("Groq client is not configured")
        active_json_mode = json_mode
        for attempt in range(2):
            try:
                options: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                }
                if active_json_mode:
                    options["response_format"] = {"type": "json_object"}
                return self.client.chat.completions.create(**options)
            except RateLimitError as exc:
                if attempt:
                    raise
                retry_after = self._retry_after(exc)
                time.sleep(min(max(retry_after, 0.0), 2.0))
            except (APITimeoutError, APIConnectionError):
                if attempt:
                    raise
                time.sleep(0.25)
            except APIStatusError as exc:
                if active_json_mode and exc.status_code == 400:
                    active_json_mode = False
                    continue
                if attempt or exc.status_code < 500:
                    raise
                time.sleep(0.25)
        raise RuntimeError("Groq request failed after bounded retries")

    @staticmethod
    def _retry_after(exc: APIStatusError) -> float:
        value = exc.response.headers.get("retry-after", "0")
        try:
            return float(value)
        except (TypeError, ValueError):
            try:
                date = email.utils.parsedate_to_datetime(value)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                return max(0.0, (date - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return 0.0

    @staticmethod
    def _error_code(exc: Exception) -> str:
        if isinstance(exc, RateLimitError):
            return "rate_limited"
        if isinstance(exc, (APITimeoutError, TimeoutError)):
            return "timeout"
        if isinstance(exc, APIStatusError):
            if exc.status_code in {401, 403}:
                return "authentication_failed"
            if exc.status_code == 404:
                return "invalid_model_or_endpoint"
            if exc.status_code == 429:
                return "rate_limited"
            return f"provider_http_{exc.status_code}"
        if isinstance(exc, APIConnectionError):
            return "connection_error"
        if isinstance(exc, ValueError):
            return "invalid_response"
        return "provider_unavailable"

    def status(self) -> dict[str, str | bool | None]:
        if self.client is not None:
            state = "configured"
            model = self.settings.fast_model
        elif self.settings.replay:
            state = "replay"
            model = None
        else:
            state = "not_configured"
            model = None
        return {
            "provider": "groq",
            "state": state,
            "model": model,
            "last_error": self.last_error,
            "credentials_configured": bool(self.settings.groq_api_key),
        }

    async def check_connection(self) -> dict[str, Any]:
        if self.client is None:
            return {
                "provider": "groq",
                "reachable": False,
                "state": "replay" if self.settings.replay else "not_configured",
                "error": "GROQ_API_KEY is not configured",
            }
        try:
            response = await asyncio.to_thread(self.client.models.list)
            available_ids = {item.id for item in response.data}
            configured_models = {
                "fast": self.settings.fast_model,
                "smart": self.settings.smart_model,
                "vision": self.settings.vision_model,
            }
            self.last_error = None
            return {
                "provider": "groq",
                "reachable": True,
                "state": "connected",
                "configured_models_available": {
                    role: model in available_ids for role, model in configured_models.items()
                },
            }
        except (RateLimitError, APITimeoutError, APIConnectionError, APIStatusError) as exc:
            error = self._error_code(exc)
            self.last_error = error
            return {"provider": "groq", "reachable": False, "state": "error", "error": error}

    def _deterministic_reply(self, prompt: str) -> str:
        try:
            request = json.loads(prompt)
        except (TypeError, json.JSONDecodeError):
            request = {}
        return str(request.get("fallback") or "Live AI assistance is unavailable. Please use the verified claim details and next steps shown.")


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return LLMClient()

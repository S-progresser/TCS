from __future__ import annotations

import time
from types import SimpleNamespace

import httpx
import pytest
from openai import APIStatusError, APITimeoutError, RateLimitError

from backend.app import llm
from backend.app.agents.explainer_verifier import ExplainerVerifier
from backend.app.deterministic import build_concierge_plan
from backend.app.llm import LLMClient


def api_error(error_type, status: int, headers: dict[str, str] | None = None):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(status, request=request, headers=headers or {})
    return error_type("mock provider error", response=response, body={"error": {"message": "mock"}})


class MockCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=outcome))])


def fake_client(*outcomes):
    client = LLMClient.__new__(LLMClient)
    client.settings = SimpleNamespace(
        groq_api_key="test-key",
        groq_base_url="https://api.groq.com/openai/v1",
        fast_model="openai/gpt-oss-20b",
        smart_model="openai/gpt-oss-120b",
        vision_model="qwen/qwen3.8-27b",
        replay=False,
    )
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=MockCompletions(outcomes)))
    client.last_error = None
    return client


@pytest.mark.asyncio
async def test_groq_configuration_and_successful_json_response(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "unit-test-secret")
    monkeypatch.setenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    llm.get_settings.cache_clear()
    client = LLMClient()
    assert client.client is not None
    assert str(client.client.base_url) == "https://api.groq.com/openai/v1/"
    assert "unit-test-secret" not in str(client.status())

    mocked = fake_client('{"answer":"claim is in review"}')
    result = await mocked.generate_result('{"fallback":"safe answer"}', json_mode=True)
    assert result.provider == "groq"
    assert result.content == '{"answer":"claim is in review"}'
    assert mocked.client.chat.completions.calls[0]["response_format"] == {"type": "json_object"}
    llm.get_settings.cache_clear()
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_BASE_URL", raising=False)


@pytest.mark.asyncio
async def test_invalid_model_errors_fall_back_explicitly():
    client = fake_client(api_error(APIStatusError, 404))
    result = await client.generate_result('{"fallback":"claim facts only"}')
    assert result.provider == "deterministic"
    assert result.fallback is True
    assert result.error == "invalid_model_or_endpoint"
    assert client.last_error == "invalid_model_or_endpoint"


@pytest.mark.asyncio
async def test_rate_limit_respects_retry_after_with_a_bounded_retry(monkeypatch):
    sleeps = []
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)
    client = fake_client(api_error(RateLimitError, 429, {"retry-after": "5"}), "ok")
    result = await client.generate_result("prompt")
    assert result.provider == "groq"
    assert len(client.client.chat.completions.calls) == 2
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_timeout_retries_once_then_reports_deterministic_fallback(monkeypatch):
    sleeps = []
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    client = fake_client(APITimeoutError(request=request), APITimeoutError(request=request))
    result = await client.generate_result('{"fallback":"verified local response"}')
    assert result.provider == "deterministic"
    assert result.error == "timeout"
    assert result.content == "verified local response"
    assert sleeps == [0.25]
    assert len(client.client.chat.completions.calls) == 2


@pytest.mark.asyncio
async def test_outer_llm_timeout_returns_deterministic_fallback(monkeypatch):
    client = fake_client("unused")

    def slow_completion(*args, **kwargs):
        time.sleep(0.1)
        return None

    monkeypatch.setattr(client, "_complete", slow_completion)
    monkeypatch.setattr(llm, "LLM_CALL_TIMEOUT_SECONDS", 0.01)
    result = await client.generate_result('{"fallback":"verified findings remain available"}')
    assert result.provider == "deterministic"
    assert result.fallback
    assert result.error == "timeout"
    assert result.content == "verified findings remain available"


@pytest.mark.asyncio
async def test_no_credentials_uses_labeled_deterministic_or_replay_fallback():
    client = LLMClient.__new__(LLMClient)
    client.settings = SimpleNamespace(
        groq_api_key=None,
        fast_model="openai/gpt-oss-20b",
        replay=False,
    )
    client.client = None
    client.last_error = None
    result = await client.generate_result('{"fallback":"local safe response"}')
    assert result.provider == "deterministic"
    assert result.fallback
    assert result.content == "local safe response"
    client.settings.replay = True
    replay = await client.generate_result('{"fallback":"replayed"}')
    assert replay.provider == "replay"


@pytest.mark.asyncio
async def test_invalid_structured_explainer_response_is_not_reported_as_groq(monkeypatch):
    monkeypatch.setattr("backend.app.agents.explainer_verifier.get_llm_client", lambda: fake_client("not json"))
    investigation = SimpleNamespace(evidence=["A matching policy excerpt."], citations=["Policy Handbook"])
    result = await ExplainerVerifier().compose(
        claim={"id": "CLM-3021", "status": "Document review", "analysis": {"next_steps": ["Upload the invoice"]}},
        investigation=investigation,
        plan=build_concierge_plan("claim status", claim_id="CLM-3021"),
        fallback_answer="Claim CLM-3021 is in document review.",
    )
    assert result.provider == "deterministic"
    assert result.answer == "Claim CLM-3021 is in document review."
    assert result.citations == ["Policy Handbook"]


def test_frontend_source_contains_no_groq_credentials():
    from pathlib import Path

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "src"
    for path in frontend.rglob("*"):
        if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".css"}:
            assert "GROQ_API_KEY=" not in path.read_text(encoding="utf-8")

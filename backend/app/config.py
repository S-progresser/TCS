from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    project_name: str = "ClaimSense"
    app_version: str = "0.1.0"
    debug: bool = False
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    fast_model: str = "openai/gpt-oss-20b"
    smart_model: str = "openai/gpt-oss-120b"
    vision_model: str = "qwen/qwen3.8-27b"
    stt_model: str = "distil-whisper-large-v3-en"
    fallback_model: str = "openai/gpt-oss-20b"
    replay: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        groq_base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        fast_model=os.getenv("FAST_MODEL", "openai/gpt-oss-20b"),
        smart_model=os.getenv("SMART_MODEL", "openai/gpt-oss-120b"),
        vision_model=os.getenv("VISION_MODEL", "qwen/qwen3.8-27b"),
        stt_model=os.getenv("STT_MODEL", "distil-whisper-large-v3-en"),
        fallback_model=os.getenv("FALLBACK_MODEL", "openai/gpt-oss-20b"),
        replay=os.getenv("REPLAY", "false").lower() in {"1", "true", "yes"},
    )

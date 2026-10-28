from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    project_name: str = "ClaimSense"
    app_version: str = "0.1.0"
    debug: bool = False
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    fast_model: str = "llama-3.1-8b-instant"
    smart_model: str = "llama-3.3-70b-versatile"
    vision_model: str = "llama-3.2-90b-vision-preview"
    stt_model: str = "distil-whisper-large-v3-en"
    fallback_model: str = "meta-llama/llama-3.1-70b-instruct"
    replay: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY") or None,
        fast_model=os.getenv("FAST_MODEL", "llama-3.1-8b-instant"),
        smart_model=os.getenv("SMART_MODEL", "llama-3.3-70b-versatile"),
        vision_model=os.getenv("VISION_MODEL", "llama-3.2-90b-vision-preview"),
        stt_model=os.getenv("STT_MODEL", "distil-whisper-large-v3-en"),
        fallback_model=os.getenv("FALLBACK_MODEL", "meta-llama/llama-3.1-70b-instruct"),
        replay=os.getenv("REPLAY", "false").lower() in {"1", "true", "yes"},
    )

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv


def _load_env() -> None:
    # Prefer .env.local if present; fall back to standard .env
    cwd = Path.cwd()
    local_env = cwd / ".env.local"
    if local_env.exists():
        load_dotenv(dotenv_path=local_env)
    else:
        load_dotenv()


_load_env()


LLMProvider = Literal["openai", "anthropic"]


class Settings:
    def __init__(self) -> None:
        self.llm_provider: LLMProvider = cast_provider(os.getenv("LLM_PROVIDER", "openai"))
        self.model: str = os.getenv("MODEL", "gpt-4o-mini")
        self.openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
        # Path to the system prompt markdown file
        self.prompt_path: Path = Path(os.getenv("PROMPT_PATH", "./prompt-parser.md")).resolve()
        # Strict JSON response enforcement (best-effort for Anthropic)
        self.enforce_json: bool = os.getenv("ENFORCE_JSON", "true").lower() in {"1", "true", "yes"}


def cast_provider(value: str) -> LLMProvider:
    val = value.lower().strip()
    if val not in {"openai", "anthropic"}:
        return "openai"
    return val  # type: ignore[return-value]


settings = Settings()



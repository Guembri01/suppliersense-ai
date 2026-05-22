import json
from functools import cached_property
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./suppliersense.db"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Stored as raw string to avoid pydantic-settings auto-JSON-decoding
    # (which would reject comma-separated env values). Use `.allowed_origins`
    # for the parsed list.
    ALLOWED_ORIGINS_RAW: str = "http://localhost:5030,http://localhost:3000"

    RATE_LIMIT_PER_MINUTE: int = 60

    # AI providers
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    DEEPINFRA_API_KEY: str = ""
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"
    WHISPER_MODEL: str = "openai/whisper-large-v3"
    MOCK_WHISPER: bool = False
    MOCK_LLM: bool = False
    AZURE_DI_ENDPOINT: str = ""
    AZURE_DI_KEY: str = ""

    SKIP_SEED: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_aliases={"ALLOWED_ORIGINS_RAW": "ALLOWED_ORIGINS"},
        populate_by_name=True,
    )

    @cached_property
    def ALLOWED_ORIGINS(self) -> List[str]:
        raw = (self.ALLOWED_ORIGINS_RAW or "").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except json.JSONDecodeError:
                pass
        return [part.strip() for part in raw.split(",") if part.strip()]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        weak = {
            "change-me-in-production",
            "change-me-before-production",
            "secret",
            "your_secret_key_here",
            "",
        }
        if v.lower() in weak or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 chars and not a known weak default")
        return v


settings = Settings()

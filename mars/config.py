"""Configuration, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    db_path: str
    verify_token: str
    app_secret: str
    access_token: str
    phone_number_id: str
    anthropic_api_key: str
    summary_model: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            db_path=os.environ.get("MARS_DB_PATH", "data/mars.db"),
            verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN", ""),
            app_secret=os.environ.get("WHATSAPP_APP_SECRET", ""),
            access_token=os.environ.get("WHATSAPP_ACCESS_TOKEN", ""),
            phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID", ""),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            summary_model=os.environ.get("MARS_SUMMARY_MODEL", "claude-sonnet-4-6"),
        )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

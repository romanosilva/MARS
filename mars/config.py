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
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_to: str
    smtp_starttls: bool

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
            smtp_host=os.environ.get("MARS_SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.environ.get("MARS_SMTP_PORT", "587")),
            smtp_user=os.environ.get("MARS_SMTP_USER", ""),
            smtp_password=os.environ.get("MARS_SMTP_PASSWORD", ""),
            smtp_from=os.environ.get("MARS_SMTP_FROM", ""),
            smtp_to=os.environ.get("MARS_DIGEST_TO", ""),
            smtp_starttls=os.environ.get("MARS_SMTP_STARTTLS", "true").lower()
            != "false",
        )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password
                    and self.smtp_to)

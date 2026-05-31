"""Send a plain-text email via SMTP (stdlib only).

Designed for Gmail SMTP with an app password, but works with any SMTP server.
The standalone digest job runs outside the Claude session, so it sends mail
itself rather than going through any chat-side connector.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from ..config import Config


def build_message(config: Config, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.smtp_from or config.smtp_user
    msg["To"] = config.smtp_to
    msg.set_content(body)
    return msg


def send(config: Config, subject: str, body: str) -> None:
    """Send the email. Raises RuntimeError if SMTP isn't configured."""
    if not config.smtp_configured:
        raise RuntimeError(
            "SMTP not configured. Set MARS_SMTP_USER, MARS_SMTP_PASSWORD, "
            "and MARS_DIGEST_TO (see .env.example).")
    msg = build_message(config, subject, body)
    with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
        if config.smtp_starttls:
            server.starttls()
        server.login(config.smtp_user, config.smtp_password)
        server.send_message(msg)

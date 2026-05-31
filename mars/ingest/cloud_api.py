"""WhatsApp Cloud API helpers: webhook signature checks and payload parsing.

The Cloud API delivers *inbound* messages as webhook events. It does not
replay your past history and does not echo messages you send (only delivery
statuses), so outbound capture happens at send time via log_outbound().
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from ..models import INBOUND, OUTBOUND, Message

# Cloud API message types we store a text body for; others are kept as type only.
_TEXT_LIKE = {"text", "button", "interactive"}


def verify_signature(app_secret: str, raw_body: bytes, header: str) -> bool:
    """Validate Meta's X-Hub-Signature-256 header against the raw request body."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body,
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


def verify_subscription(verify_token: str, mode: str, token: str,
                        challenge: str) -> Optional[str]:
    """Handle the GET verification handshake. Returns the challenge if valid."""
    if mode == "subscribe" and token == verify_token:
        return challenge
    return None


def _extract_text(msg: dict) -> str:
    t = msg.get("type")
    if t == "text":
        return msg.get("text", {}).get("body", "")
    if t == "button":
        return msg.get("button", {}).get("text", "")
    if t == "interactive":
        inter = msg.get("interactive", {})
        for key in ("button_reply", "list_reply"):
            if key in inter:
                return inter[key].get("title", "")
    return ""


def parse_webhook(payload: dict) -> list[Message]:
    """Turn one webhook POST body into a list of inbound Messages.

    Contact display names ride along in value['contacts']; we map them onto
    each message's chat for nicer profiles. Returns [] for status-only events.
    """
    messages: list[Message] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            names = {c.get("wa_id"): c.get("profile", {}).get("name", "")
                     for c in value.get("contacts", [])}
            for msg in value.get("messages", []):
                wa_id = msg.get("from", "")
                mtype = msg.get("type", "unknown")
                try:
                    ts = int(msg.get("timestamp", "0"))
                except (TypeError, ValueError):
                    ts = 0
                body = _extract_text(msg) if mtype in _TEXT_LIKE else ""
                messages.append(Message(
                    msg_id=msg.get("id", f"{wa_id}:{ts}"),
                    chat_id=wa_id,            # 1:1 chat keyed by contact
                    sender_id=names.get(wa_id) or wa_id,
                    direction=INBOUND,
                    ts=ts,
                    msg_type=mtype,
                    body=body,
                    source="cloud_api",
                ))
    return messages


def contact_names(payload: dict) -> dict[str, str]:
    """Collect {wa_id: display_name} pairs from a webhook payload."""
    out: dict[str, str] = {}
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for c in change.get("value", {}).get("contacts", []):
                wa_id = c.get("wa_id")
                name = c.get("profile", {}).get("name", "")
                if wa_id:
                    out[wa_id] = name
    return out


def log_outbound(to_wa_id: str, text: str, ts: int, msg_id: str) -> Message:
    """Build an OUTBOUND Message to store when you send a reply via MARS."""
    return Message(
        msg_id=msg_id, chat_id=to_wa_id, sender_id="me",
        direction=OUTBOUND, ts=ts, msg_type="text", body=text,
        source="cloud_api",
    )

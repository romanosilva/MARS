"""Plain data structures shared across ingestion and analysis."""

from __future__ import annotations

from dataclasses import dataclass

# Direction of a message relative to the account owner ("you").
INBOUND = "in"    # sent to you by a contact
OUTBOUND = "out"  # sent by you


@dataclass
class Message:
    """One normalized message, regardless of source."""

    msg_id: str          # stable id (Cloud API id, or synthesized for exports)
    chat_id: str         # 1:1 chat == contact wa_id; groups get their own id
    sender_id: str       # wa_id / display name of whoever sent it
    direction: str       # INBOUND or OUTBOUND
    ts: int              # unix seconds
    msg_type: str        # text, image, audio, document, system, ...
    body: str            # text content (empty for media without caption)
    source: str          # "cloud_api" or "export"

    def __post_init__(self) -> None:
        if self.direction not in (INBOUND, OUTBOUND):
            raise ValueError(f"invalid direction: {self.direction!r}")


@dataclass
class Contact:
    wa_id: str
    display_name: str
    first_seen_ts: int
    last_seen_ts: int

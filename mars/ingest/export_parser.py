"""Parse WhatsApp 'Export Chat' .txt files into normalized Messages.

WhatsApp exports vary by phone locale and OS. We handle the two dominant
layouts and several date orderings:

    iOS:     [2024/01/15, 14:30:45] Jane Doe: hello
    Android: 15/01/2024, 14:30 - Jane Doe: hello
    Android: 1/15/24, 2:30 PM - Jane Doe: hello

Lines without a leading timestamp are treated as continuations of the
previous message (multi-line messages). Timestamped lines with no
"Name: " segment are treated as system notices and skipped from the
conversation (e.g. "Messages are end-to-end encrypted").
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..models import INBOUND, OUTBOUND, Message

# Leading-timestamp matchers. Group 'date', 'time', 'rest'.
_IOS = re.compile(r"^\[(?P<date>[^,\]]+),\s*(?P<time>[^\]]+)\]\s?(?P<rest>.*)$")
_ANDROID = re.compile(
    r"^(?P<date>\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}),\s*"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?)\s-\s(?P<rest>.*)$"
)

# Media placeholders WhatsApp inserts when media is excluded from export.
_MEDIA_OMITTED = re.compile(r"<.*omitted>|‎?image omitted|‎?video omitted",
                            re.IGNORECASE)

_DATE_FORMATS = [
    "%Y/%m/%d", "%Y-%m-%d",
    "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y",
    "%d/%m/%y", "%m/%d/%y", "%d.%m.%y",
]
_TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]


@dataclass
class _Raw:
    ts: int
    sender: Optional[str]  # None => system line
    body: str


def _parse_ts(date_s: str, time_s: str, dayfirst: bool = True) -> Optional[int]:
    date_s, time_s = date_s.strip(), time_s.strip().replace(" ", " ").upper()
    # Order date formats so the preferred day/month interpretation wins.
    fmts = _DATE_FORMATS if dayfirst else (
        [f for f in _DATE_FORMATS if f.startswith("%m") or f.startswith("%Y")]
        + [f for f in _DATE_FORMATS if not (f.startswith("%m") or f.startswith("%Y"))]
    )
    for df in fmts:
        for tf in _TIME_FORMATS:
            try:
                dt = datetime.strptime(f"{date_s} {time_s}", f"{df} {tf}")
                return int(dt.timestamp())
            except ValueError:
                continue
    return None


def _split_line(line: str) -> Optional[tuple[str, str, str]]:
    """Return (date, time, rest) if the line begins a new message, else None."""
    for rx in (_IOS, _ANDROID):
        m = rx.match(line)
        if m:
            return m.group("date"), m.group("time"), m.group("rest")
    return None


def parse_raw(text: str, dayfirst: bool = True) -> list[_Raw]:
    raw: list[_Raw] = []
    for line in text.splitlines():
        # Strip LTR/RTL marks WhatsApp sprinkles into exports.
        line = line.replace("‎", "").replace("‏", "")
        if not line:
            continue
        parts = _split_line(line)
        if parts is None:
            if raw:  # continuation of previous message
                raw[-1].body += "\n" + line
            continue
        date_s, time_s, rest = parts
        ts = _parse_ts(date_s, time_s, dayfirst=dayfirst)
        if ts is None:
            if raw:
                raw[-1].body += "\n" + line
            continue
        if ": " in rest:
            sender, body = rest.split(": ", 1)
            raw.append(_Raw(ts=ts, sender=sender.strip(), body=body))
        else:
            raw.append(_Raw(ts=ts, sender=None, body=rest))  # system notice
    return raw


def to_messages(
    raw: list[_Raw],
    owner_name: str,
    chat_id: str,
    include_system: bool = False,
) -> list[Message]:
    """Convert raw lines to Messages.

    owner_name: the sender label that represents *you* in this export;
                those lines become OUTBOUND, everything else INBOUND.
    chat_id:    identifier for this conversation (e.g. the contact or group).
    """
    out: list[Message] = []
    owner = owner_name.strip().lower()
    for i, r in enumerate(raw):
        if r.sender is None:
            if not include_system:
                continue
            sender, direction, mtype = "system", INBOUND, "system"
        else:
            is_owner = r.sender.strip().lower() == owner
            sender = r.sender
            direction = OUTBOUND if is_owner else INBOUND
            mtype = "media" if _MEDIA_OMITTED.search(r.body) else "text"
        digest = hashlib.sha1(
            f"{chat_id}|{r.ts}|{r.sender}|{i}|{r.body}".encode("utf-8")
        ).hexdigest()[:20]
        out.append(Message(
            msg_id=f"exp_{digest}", chat_id=chat_id, sender_id=sender,
            direction=direction, ts=r.ts, msg_type=mtype, body=r.body,
            source="export",
        ))
    return out


def parse_export(
    text: str, owner_name: str, chat_id: str,
    dayfirst: bool = True, include_system: bool = False,
) -> list[Message]:
    return to_messages(parse_raw(text, dayfirst=dayfirst),
                       owner_name, chat_id, include_system=include_system)

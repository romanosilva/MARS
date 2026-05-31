"""Patterns & analytics over the whole store or a single chat."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..models import INBOUND, OUTBOUND, Message


@dataclass
class Analytics:
    total: int = 0
    inbound: int = 0
    outbound: int = 0
    by_contact: Counter = field(default_factory=Counter)     # chat_id -> count
    by_hour: Counter = field(default_factory=Counter)        # 0..23 -> count
    by_weekday: Counter = field(default_factory=Counter)     # 0=Mon..6=Sun
    your_reply_secs: list[int] = field(default_factory=list)
    their_reply_secs: list[int] = field(default_factory=list)

    @property
    def response_ratio(self) -> float:
        return self.outbound / self.inbound if self.inbound else float("inf")


def _reply_latencies(messages: list[Message]) -> tuple[list[int], list[int]]:
    """For one chat (time-sorted), return (your_reply_secs, their_reply_secs).

    A latency is measured from the first message of an incoming run to the
    first message of the answering run in the other direction.
    """
    yours: list[int] = []
    theirs: list[int] = []
    msgs = [m for m in messages if m.msg_type != "system"]
    if not msgs:
        return yours, theirs
    run_dir = msgs[0].direction
    run_start = msgs[0].ts
    for m in msgs[1:]:
        if m.direction == run_dir:
            continue
        delta = m.ts - run_start
        if delta >= 0:
            (yours if m.direction == OUTBOUND else theirs).append(delta)
        run_dir = m.direction
        run_start = m.ts
    return yours, theirs


def compute(messages: list[Message]) -> Analytics:
    a = Analytics()
    per_chat: dict[str, list[Message]] = defaultdict(list)
    for m in messages:
        per_chat[m.chat_id].append(m)
        if m.msg_type == "system":
            continue
        a.total += 1
        if m.direction == INBOUND:
            a.inbound += 1
        else:
            a.outbound += 1
        a.by_contact[m.chat_id] += 1
        dt = datetime.fromtimestamp(m.ts, tz=timezone.utc)
        a.by_hour[dt.hour] += 1
        a.by_weekday[dt.weekday()] += 1
    for chat_msgs in per_chat.values():
        chat_msgs.sort(key=lambda m: m.ts)
        y, t = _reply_latencies(chat_msgs)
        a.your_reply_secs.extend(y)
        a.their_reply_secs.extend(t)
    return a


def _fmt_secs(secs: float) -> str:
    if secs < 90:
        return f"{int(secs)}s"
    if secs < 5400:
        return f"{secs / 60:.0f}m"
    if secs < 172800:
        return f"{secs / 3600:.1f}h"
    return f"{secs / 86400:.1f}d"


_WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def render(a: Analytics, name_of=lambda cid: cid, top: int = 8) -> str:
    lines = ["=== Patterns & Analytics ===",
             f"Messages: {a.total}  (in {a.inbound} / out {a.outbound})"]
    if a.inbound:
        lines.append(f"Reply ratio (out:in): {a.response_ratio:.2f}")
    if a.your_reply_secs:
        lines.append(f"Your median reply time:  "
                     f"{_fmt_secs(statistics.median(a.your_reply_secs))}")
    if a.their_reply_secs:
        lines.append(f"Their median reply time: "
                     f"{_fmt_secs(statistics.median(a.their_reply_secs))}")
    if a.by_hour:
        busy = sorted(a.by_hour.items(), key=lambda kv: -kv[1])[:3]
        lines.append("Busiest hours (UTC): "
                     + ", ".join(f"{h:02d}:00 ({c})" for h, c in busy))
    if a.by_weekday:
        busy_d = sorted(a.by_weekday.items(), key=lambda kv: -kv[1])[:3]
        lines.append("Busiest days: "
                     + ", ".join(f"{_WD[d]} ({c})" for d, c in busy_d))
    if a.by_contact:
        lines.append("\nTop contacts by volume:")
        for cid, c in a.by_contact.most_common(top):
            lines.append(f"  {name_of(cid):<28} {c}")
    return "\n".join(lines)

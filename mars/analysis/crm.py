"""Follow-up / CRM view: who is waiting on whom, and for how long."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from ..models import INBOUND, OUTBOUND, Message


@dataclass
class ThreadState:
    chat_id: str
    name: str
    last_ts: int
    last_direction: str
    last_snippet: str
    awaiting_you: bool       # they messaged last -> you owe a reply
    age_secs: int


def _snippet(body: str, n: int = 70) -> str:
    body = body.replace("\n", " ").strip()
    return body if len(body) <= n else body[: n - 1] + "…"


def thread_states(per_chat: dict[str, list[Message]],
                  names: dict[str, str],
                  now: int | None = None) -> list[ThreadState]:
    now = now or int(time.time())
    states: list[ThreadState] = []
    for chat_id, msgs in per_chat.items():
        convo = [m for m in msgs if m.msg_type != "system"]
        if not convo:
            continue
        last = max(convo, key=lambda m: m.ts)
        states.append(ThreadState(
            chat_id=chat_id,
            name=names.get(chat_id, chat_id),
            last_ts=last.ts,
            last_direction=last.direction,
            last_snippet=_snippet(last.body) or f"[{last.msg_type}]",
            awaiting_you=last.direction == INBOUND,
            age_secs=max(0, now - last.ts),
        ))
    return states


def _fmt_age(secs: int) -> str:
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


def render_followups(states: list[ThreadState], min_age_secs: int = 0) -> str:
    owe = sorted([s for s in states if s.awaiting_you and s.age_secs >= min_age_secs],
                 key=lambda s: -s.age_secs)
    waiting = sorted([s for s in states if not s.awaiting_you],
                     key=lambda s: -s.age_secs)
    lines = ["=== Follow-up / CRM ===",
             f"\nYou owe a reply ({len(owe)}):"]
    if not owe:
        lines.append("  (all caught up)")
    for s in owe:
        when = datetime.fromtimestamp(s.last_ts, tz=timezone.utc).strftime("%Y-%m-%d")
        lines.append(f"  [{_fmt_age(s.age_secs):>4} ago] {s.name:<24} "
                     f"{when}  “{s.last_snippet}”")
    lines.append(f"\nWaiting on them ({len(waiting)}):")
    for s in waiting[:20]:
        lines.append(f"  [{_fmt_age(s.age_secs):>4} ago] {s.name:<24} "
                     f"“{s.last_snippet}”")
    return "\n".join(lines)

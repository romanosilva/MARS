"""Build the daily follow-up digest (subject + body) from thread states."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from .crm import ThreadState, _fmt_age

DAY = 86400


def build(states: list[ThreadState], now: int | None = None,
          owe_min_secs: int = 0, new_window_secs: int = DAY) -> tuple[str, str]:
    now = now or int(time.time())
    owe = sorted(
        [s for s in states if s.awaiting_you and s.age_secs >= owe_min_secs],
        key=lambda s: -s.age_secs)
    fresh = [s for s in owe if s.age_secs <= new_window_secs]
    stale = [s for s in owe if s.age_secs > 2 * DAY]
    waiting = sorted([s for s in states if not s.awaiting_you],
                     key=lambda s: -s.age_secs)

    today = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%a %d %b %Y")
    subject = f"MARS daily — {len(owe)} repl{'y' if len(owe)==1 else 'ies'} owed"

    lines = [f"MARS follow-up digest · {today} (UTC)", ""]
    if not owe:
        lines.append("✅ Inbox zero — no replies owed.")
    else:
        lines.append(f"You owe {len(owe)} repl{'y' if len(owe)==1 else 'ies'}"
                     + (f", {len(stale)} aging past 48h" if stale else "") + ":")
        lines.append("")
        for s in owe:
            flag = "🔴" if s.age_secs > 2 * DAY else ("🆕" if s in fresh else "  ")
            when = datetime.fromtimestamp(
                s.last_ts, tz=timezone.utc).strftime("%d %b")
            lines.append(f"{flag} [{_fmt_age(s.age_secs):>4}] {s.name:<24} "
                         f"{when}  “{s.last_snippet}”")

    if waiting:
        lines += ["", f"Waiting on them ({len(waiting)}):"]
        for s in waiting[:8]:
            lines.append(f"   [{_fmt_age(s.age_secs):>4}] {s.name:<24} "
                         f"“{s.last_snippet}”")

    lines += ["", "— MARS", "Reply ‘snooze <name>’ mentally; this is a read-only nudge."]
    return subject, "\n".join(lines)

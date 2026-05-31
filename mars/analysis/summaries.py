"""Per-person summaries: deterministic digest, optionally narrated by an LLM."""

from __future__ import annotations

import statistics
from datetime import datetime, timezone

from ..config import Config
from ..models import INBOUND, OUTBOUND, Message
from . import analytics, heuristics, llm, text


def _date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def digest(name: str, messages: list[Message]) -> str:
    """Deterministic, no-network summary of one contact."""
    convo = sorted([m for m in messages if m.msg_type != "system"],
                   key=lambda m: m.ts)
    if not convo:
        return f"{name}: no messages."
    a = analytics.compute(convo)
    kw = text.keywords((m.body for m in convo), top=10)
    commits = heuristics.commitments(convo)
    asks = heuristics.open_requests(convo)

    lines = [f"=== Summary: {name} ===",
             f"{a.total} messages ({a.inbound} in / {a.outbound} out), "
             f"{_date(convo[0].ts)} → {_date(convo[-1].ts)}"]
    if a.your_reply_secs:
        lines.append("Your median reply: "
                     + analytics._fmt_secs(statistics.median(a.your_reply_secs)))
    if kw:
        lines.append("Topics: " + ", ".join(w for w, _ in kw))
    if asks:
        lines.append("\nThey recently asked:")
        lines += [f"  • {m.body.splitlines()[0][:90]}" for m in asks]
    if commits:
        lines.append("\nYou committed to:")
        lines += [f"  • {m.body.splitlines()[0][:90]}" for m in commits]
    return "\n".join(lines)


def _transcript(messages: list[Message], max_msgs: int = 120) -> str:
    convo = sorted([m for m in messages if m.msg_type != "system"],
                   key=lambda m: m.ts)[-max_msgs:]
    who = {INBOUND: "Them", OUTBOUND: "You"}
    return "\n".join(
        f"[{_date(m.ts)}] {who[m.direction]}: {m.body or '[' + m.msg_type + ']'}"
        for m in convo
    )


def summarize(config: Config, name: str, messages: list[Message]) -> str:
    """LLM-narrated summary if available, else the deterministic digest."""
    if not llm.available(config):
        return digest(name, messages)
    system = (
        "You analyze a WhatsApp conversation between the account owner ('You') "
        "and a contact ('Them'). Produce a concise profile: who the contact is, "
        "the nature of the relationship, recurring topics, the contact's apparent "
        "priorities, any open requests or commitments, and 2-3 suggested next "
        "actions. Be factual and grounded only in the transcript."
    )
    user = f"Contact: {name}\n\nTranscript:\n{_transcript(messages)}"
    try:
        return f"=== Summary: {name} (LLM) ===\n" + llm.complete(config, system, user)
    except Exception as e:  # network/SDK failure -> safe fallback
        return digest(name, messages) + f"\n\n[LLM summary unavailable: {e}]"

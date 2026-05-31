"""On-demand briefing for a single contact before you talk to them."""

from __future__ import annotations

from datetime import datetime, timezone

from ..config import Config
from ..models import INBOUND, OUTBOUND, Message
from . import heuristics, llm, text
from .summaries import _transcript


def _date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def brief(config: Config, name: str, messages: list[Message],
          recent: int = 8) -> str:
    convo = sorted([m for m in messages if m.msg_type != "system"],
                   key=lambda m: m.ts)
    if not convo:
        return f"No history with {name}."

    unanswered = heuristics.trailing_unanswered(convo)
    commits = heuristics.commitments(convo)
    asks = heuristics.open_requests(convo)
    kw = text.keywords((m.body for m in convo), top=8)

    lines = [f"=== Meeting prep: {name} ===",
             f"Last contact: {_date(convo[-1].ts)}  |  {len(convo)} messages on record"]
    if kw:
        lines.append("Recurring topics: " + ", ".join(w for w, _ in kw))

    if unanswered:
        lines.append("\n⚠ Awaiting your reply:")
        lines += [f"  • {m.body.splitlines()[0][:90]}" for m in unanswered[-4:]]
    if asks:
        lines.append("\nOpen asks from them:")
        lines += [f"  • {m.body.splitlines()[0][:90]}" for m in asks]
    if commits:
        lines.append("\nYour outstanding commitments:")
        lines += [f"  • {m.body.splitlines()[0][:90]}" for m in commits]

    lines.append("\nLast messages:")
    who = {INBOUND: "Them", OUTBOUND: "You "}
    for m in convo[-recent:]:
        lines.append(f"  [{_date(m.ts)}] {who[m.direction]}: "
                     f"{(m.body or '[' + m.msg_type + ']').splitlines()[0][:90]}")

    if llm.available(config):
        system = (
            "You are briefing the account owner before they message/meet a "
            "contact. Given the transcript, write a 4-6 line briefing: where "
            "things stand, what the contact wants, what the owner owes them, and "
            "the single most important thing to address next. Ground every claim "
            "in the transcript."
        )
        try:
            narrative = llm.complete(
                config, system,
                f"Contact: {name}\n\nTranscript:\n{_transcript(messages)}",
                max_tokens=400,
            )
            lines.append("\n--- Briefing ---\n" + narrative)
        except Exception as e:
            lines.append(f"\n[LLM briefing unavailable: {e}]")
    return "\n".join(lines)

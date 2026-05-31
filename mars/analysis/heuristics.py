"""Regex heuristics for commitments, requests, and open questions.

Deterministic and language-light. These power meeting prep and the
fallback (non-LLM) summaries; the LLM path, when enabled, supersedes them.
"""

from __future__ import annotations

import re

from ..models import INBOUND, OUTBOUND, Message

_COMMIT = re.compile(
    r"\b(i'?ll|i will|i'?m going to|let me|i can|i'?ll send|will send|"
    r"will get|i'?ll get back|i'?ll follow up|by (?:mon|tue|wed|thu|fri|sat|sun|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|tonight|"
    r"next week|end of (?:day|week)))\b",
    re.IGNORECASE,
)
_REQUEST = re.compile(
    r"(\?|\bcan you\b|\bcould you\b|\bplease\b|\bwould you\b|\bcan we\b|"
    r"\bdo you\b|\blet me know\b|\bwaiting (?:for|on)\b)",
    re.IGNORECASE,
)


def commitments(messages: list[Message], limit: int = 6) -> list[Message]:
    """Things *you* said you'd do (outbound), most recent first."""
    hits = [m for m in messages
            if m.direction == OUTBOUND and m.body and _COMMIT.search(m.body)]
    return sorted(hits, key=lambda m: -m.ts)[:limit]


def open_requests(messages: list[Message], limit: int = 6) -> list[Message]:
    """Things *they* asked of you (inbound), most recent first."""
    hits = [m for m in messages
            if m.direction == INBOUND and m.body and _REQUEST.search(m.body)]
    return sorted(hits, key=lambda m: -m.ts)[:limit]


def trailing_unanswered(messages: list[Message]) -> list[Message]:
    """The run of inbound messages at the end with no reply yet (could be empty)."""
    convo = sorted([m for m in messages if m.msg_type != "system"],
                   key=lambda m: m.ts)
    run: list[Message] = []
    for m in reversed(convo):
        if m.direction == INBOUND:
            run.append(m)
        else:
            break
    return list(reversed(run))

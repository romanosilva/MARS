"""Optional LLM narrative layer (Claude). Degrades gracefully when no key.

Only the messages for the single contact you ask about are sent — never the
whole store. If the anthropic SDK or API key is absent, callers fall back to
the deterministic digest.
"""

from __future__ import annotations

from ..config import Config


def available(config: Config) -> bool:
    if not config.llm_enabled:
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def complete(config: Config, system: str, user: str, max_tokens: int = 700) -> str:
    """Single-shot completion. Raises if unavailable; guard with available()."""
    import anthropic

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    resp = client.messages.create(
        model=config.summary_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content
                   if getattr(block, "type", None) == "text").strip()

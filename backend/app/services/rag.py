"""RAG + generative feedback layer (Phase 5) — OPTIONAL at runtime.

Chunks and embeds a shippable knowledge base, retrieves top-k chunks by role
and weak section, and asks a swappable LLM provider (Gemini by default) to
rewrite weak bullets and explain skill gaps using ONLY retrieved chunks, citing
chunk ids. Any failure or missing key yields ``ai_available=False`` and never
blocks the rule-based analysis.
"""

from __future__ import annotations

from typing import Any


def generate_ai_feedback(
    analysis: dict[str, Any], role_id: str
) -> dict[str, Any]:
    """Return ``{ai_available, generated_feedback, citations}``. (Phase 5)

    On any error or missing API key, returns ``{"ai_available": False}``.
    """
    raise NotImplementedError("Implemented in Phase 5.")

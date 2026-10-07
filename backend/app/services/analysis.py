"""Analysis orchestration: score + ATS + feedback, plus the optional AI layer.

The rule-based part is deterministic: the same stored resume and role always
produce the same output. The AI layer runs only in ``mode="ai"``, after the
rule-based analysis is complete, and any failure inside it is reported via
``ai_available=False`` instead of failing the request.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.ats import analyze_ats
from app.services.feedback import generate_feedback
from app.services.parser import detected_section_names
from app.services.scorer import score_resume

logger = logging.getLogger(__name__)

VALID_MODES: tuple[str, ...] = ("rules", "ai")


def build_rule_analysis(record: dict[str, Any], role_id: str) -> dict[str, Any]:
    """Deterministic analysis of a stored resume against one role.

    Raises:
        UnknownRoleError: If ``role_id`` is not in the catalogue.
    """
    sections, contact, stats = record["sections"], record["contact"], record["stats"]
    parse_quality = record["parse_quality"]
    ats = analyze_ats(sections, role_id, parse_quality)
    score = score_resume(sections, contact, stats)
    feedback = generate_feedback(sections, contact, stats, parse_quality, score, ats)
    return {
        "resume_id": record["id"],
        "filename": record["filename"],
        "role": {"id": ats["role_id"], "name": ats["role_name"]},
        "score": score,
        "ats": ats,
        "feedback": feedback,
        "parse_quality": parse_quality,
        "contact": contact,
        "sections_detected": detected_section_names(sections),
    }


def add_ai_layer(analysis: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Attach generated feedback, never raising.

    Returns the analysis with ``ai_available``, ``generated_feedback``,
    ``ai_unavailable_reason`` and ``retrieved_context`` set.
    """
    from app.services import rag  # imported lazily: the rules path never needs it

    try:
        result = rag.generate_ai_feedback(analysis, record)
    except Exception as exc:  # the AI layer must never break the analysis
        logger.warning("AI layer failed: %s", exc)
        result = {"ai_available": False, "reason": f"AI layer error: {type(exc).__name__}",
                  "generated_feedback": None, "retrieved_context": []}
    return {
        **analysis,
        "ai_available": result["ai_available"],
        "ai_unavailable_reason": result.get("reason"),
        "generated_feedback": result.get("generated_feedback"),
        "retrieved_context": result.get("retrieved_context", []),
    }


def build_analysis(record: dict[str, Any], role_id: str, mode: str) -> dict[str, Any]:
    """Full analysis for the API. ``mode`` is 'rules' or 'ai'."""
    analysis = {**build_rule_analysis(record, role_id), "mode": mode}
    return add_ai_layer(analysis, record) if mode == "ai" else analysis

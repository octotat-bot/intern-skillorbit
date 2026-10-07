"""Feedback rule engine (Phase 3).

A deterministic rule set (>= 25 rules). Each fired rule yields a suggestion
with ``{rule_id, suggestion, priority, estimated_impact, evidence}``. Output
is sorted by priority then estimated impact.
"""

from __future__ import annotations

from typing import Any


def generate_feedback(
    scores: dict[str, Any], ats: dict[str, Any],
    sections: dict[str, str], contact: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return prioritised, evidence-backed improvement suggestions. (Phase 3)"""
    raise NotImplementedError("Implemented in Phase 3.")

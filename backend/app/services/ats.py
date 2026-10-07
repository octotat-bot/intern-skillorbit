"""ATS keyword-match service (Phase 2).

Matches role keywords against the resume with a spaCy PhraseMatcher over
lemmatised text (honouring per-role alias maps), computes a weighted coverage
score, applies a formatting-risk penalty from parse quality, and adds a
TF-IDF cosine-similarity signal against the role description.

The ATS score is a transparent heuristic, not a vendor-verified metric.
"""

from __future__ import annotations

from typing import Any


def analyze_ats(
    raw_text: str, role_id: str, parse_quality: dict[str, Any]
) -> dict[str, Any]:
    """Compute the ATS analysis for a resume against one role.

    Returns:
        ``{ats_score, matched, missing_must_have, missing_nice_to_have,
        tfidf_similarity, format_penalty}``.
    """
    raise NotImplementedError("Implemented in Phase 2.")

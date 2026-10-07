"""ATS keyword-match analysis.

The ATS score is a transparent heuristic, not a vendor-verified metric:

    keyword  = 100 * (0.7 * must_have_coverage + 0.3 * nice_to_have_coverage)
    tfidf    = 100 * min(1, cosine_similarity / ceiling)
    blended  = (1 - 0.2) * keyword + 0.2 * tfidf
    ats      = clamp(blended - format_penalty, 0, 100)

``must_have_coverage`` is weight-based: a requirement counts when any of its
alternative skills is found. ``format_penalty`` grows as parse quality drops,
because text an ATS cannot read cannot match. All weights live in ``config``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app import config
from app.services.roles import Requirement, Role, get_role, load_catalog
from app.services.skills import SkillHit, get_skill_matcher


@dataclass(frozen=True)
class Occurrence:
    """Where a skill was found."""

    surface: str
    section: str


# ---------------------------------------------------------------------------
# Skill collection with context filtering
# ---------------------------------------------------------------------------
def _line_before(text: str, hit: SkillHit) -> str:
    """Text on the same line as the hit, up to the hit."""
    return text[text.rfind("\n", 0, hit.start) + 1: hit.start].lower()


def _ignore_reason(section: str, text: str, hit: SkillHit) -> str | None:
    """Why a hit does not count as a claimed skill, or None if it counts."""
    if section in config.ATS_IGNORED_SECTIONS:
        return f"Mentioned only in an unscored section ({section})"
    cue = next((c for c in config.IRRELEVANT_CONTEXT_CUES if c in _line_before(text, hit)), None)
    return f"Preceded by '{cue}', so it is an intention, not a skill" if cue else None


def collect_skills(sections: dict[str, str]) -> tuple[dict[str, list[Occurrence]], list[dict[str, str]]]:
    """Find every known skill per section, separating counted from ignored hits.

    Returns:
        ``(found, ignored)``: canonical skill -> occurrences, and ignored hits
        with the reason they were discarded.
    """
    matcher = get_skill_matcher()
    found: dict[str, list[Occurrence]] = defaultdict(list)
    ignored: list[dict[str, str]] = []
    for section, text in sections.items():
        for hit in matcher.find(text):
            reason = _ignore_reason(section, text, hit)
            if reason:
                ignored.append({"skill": hit.skill, "surface": hit.surface,
                                "section": section, "reason": reason})
            else:
                found[hit.skill].append(Occurrence(hit.surface, section))
    # A skill counted anywhere is not "ignored", even if it was also ignored elsewhere.
    ignored = [item for item in ignored if item["skill"] not in found]
    return dict(found), ignored


# ---------------------------------------------------------------------------
# Keyword coverage
# ---------------------------------------------------------------------------
def _evidence(skills: list[str], found: dict[str, list[Occurrence]]) -> dict[str, list[str]]:
    """Distinct (case-insensitive) surface forms and sections for the matched skills, in order seen."""
    occurrences = [o for skill in skills for o in found[skill]]
    surfaces: dict[str, str] = {}
    for occurrence in occurrences:
        surfaces.setdefault(occurrence.surface.casefold(), occurrence.surface)
    return {
        "found_as": list(surfaces.values()),
        "sections": list(dict.fromkeys(o.section for o in occurrences)),
    }


def _evaluate_must_have(req: Requirement, found: dict[str, list[Occurrence]]) -> dict[str, Any]:


    """Match one weighted requirement against found skills."""
    catalog = load_catalog()
    hits = [skill for skill in req.any_of if skill in found]
    return {
        "label": req.label,
        "type": "must_have",
        "weight": req.weight,
        "matched": bool(hits),
        "alternatives": [catalog.display(s) for s in req.any_of],
        "skills": [catalog.display(s) for s in hits],
        **_evidence(hits, found),
    }


def _evaluate_nice(skill: str, found: dict[str, list[Occurrence]]) -> dict[str, Any]:


    """Match one nice-to-have skill against found skills."""
    label = load_catalog().display(skill)
    matched = skill in found
    return {
        "label": label,
        "type": "nice_to_have",
        "weight": 1.0,
        "matched": matched,
        "alternatives": [label],
        "skills": [label] if matched else [],
        **_evidence([skill] if matched else [], found),
    }


def _coverage(items: list[dict[str, Any]]) -> float:


    """Weighted share of items that matched (0 when there are none)."""
    total = sum(item["weight"] for item in items)
    return sum(item["weight"] for item in items if item["matched"]) / total if total else 0.0


def keyword_score(must_coverage: float, nice_coverage: float, has_nice: bool) -> float:
    """Weighted blend of must-have and nice-to-have coverage on a 0-100 scale.

    If a role has no nice-to-haves, must-have coverage carries the full weight.
    """
    must_w, nice_w = config.ATS_MUST_HAVE_WEIGHT, config.ATS_NICE_TO_HAVE_WEIGHT
    if not has_nice:
        return 100 * must_coverage
    return 100 * (must_w * must_coverage + nice_w * nice_coverage) / (must_w + nice_w)


# ---------------------------------------------------------------------------
# TF-IDF similarity
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"[a-z][a-z0-9+#]*(?:[./-][a-z0-9+#]+)*")
_STEMMER = PorterStemmer()


def tokenize(text: str) -> list[str]:
    """Lower-case, drop stop words, and Porter-stem (NLTK) so word forms align."""
    return [
        _STEMMER.stem(token)
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) > 1 and token not in ENGLISH_STOP_WORDS
    ]


def role_document(role: Role) -> str:
    """Text representing a role: its description plus all of its skill names."""
    skills = [s for req in role.must_have for s in req.any_of] + list(role.nice_to_have)
    return " ".join([role.description, *(req.label for req in role.must_have), *skills])


@lru_cache(maxsize=1)
def _role_vectors() -> tuple[TfidfVectorizer, dict[str, Any]]:
    """TF-IDF model fitted on all role documents (deterministic, cached)."""
    roles = load_catalog().roles
    vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                                 ngram_range=(1, 2), sublinear_tf=True)
    matrix = vectorizer.fit_transform([role_document(r) for r in roles.values()])
    return vectorizer, {role_id: matrix[i] for i, role_id in enumerate(roles)}


def tfidf_similarity(text: str, role_id: str) -> float:
    """Cosine similarity between resume text and the role document, in [0, 1]."""
    if not text.strip():
        return 0.0
    vectorizer, role_vectors = _role_vectors()
    return float(cosine_similarity(vectorizer.transform([text]), role_vectors[role_id])[0, 0])


# ---------------------------------------------------------------------------
# Formatting penalty and final score
# ---------------------------------------------------------------------------
def format_penalty(parse_quality: dict[str, Any]) -> dict[str, Any]:
    """Penalty proportional to lost parse quality, with the issues that caused it."""
    quality_score = parse_quality.get("score", 100)
    points = round(config.ATS_FORMAT_PENALTY_MAX * (100 - quality_score) / 100, config.SCORE_DECIMALS)
    issues = [issue["code"] for issue in parse_quality.get("issues", [])]
    return {
        "points": points,
        "parse_quality_score": quality_score,
        "issues": issues,
        "detail": f"Parse quality {quality_score}/100" + (f" ({', '.join(issues)})" if issues else ""),
    }


def analyze_ats(sections: dict[str, str], role_id: str, parse_quality: dict[str, Any]) -> dict[str, Any]:
    """Compute the ATS keyword analysis for a resume against one role.

    Raises:
        UnknownRoleError: If ``role_id`` is not in the catalogue.
    """
    role = get_role(role_id)
    catalog = load_catalog()
    found, ignored = collect_skills(sections)
    must = [_evaluate_must_have(req, found) for req in role.must_have]
    nice = [_evaluate_nice(skill, found) for skill in role.nice_to_have]
    must_cov, nice_cov = _coverage(must), _coverage(nice)
    keywords = keyword_score(must_cov, nice_cov, bool(nice))

    counted_text = "\n".join(t for s, t in sections.items() if s not in config.ATS_IGNORED_SECTIONS)
    similarity = tfidf_similarity(counted_text, role_id)
    tfidf_score = 100 * min(1.0, similarity / config.ATS_TFIDF_SIMILARITY_CEILING)
    blended = (1 - config.ATS_TFIDF_WEIGHT) * keywords + config.ATS_TFIDF_WEIGHT * tfidf_score
    penalty = format_penalty(parse_quality)
    ats_score = int(round(min(100.0, max(0.0, blended - penalty["points"]))))

    return {
        "role_id": role.id,
        "role_name": role.name,
        "ats_score": ats_score,
        "keyword_score": round(keywords, config.SCORE_DECIMALS),
        "must_have_coverage": round(must_cov, 3),
        "nice_to_have_coverage": round(nice_cov, 3),
        "tfidf": {"similarity": round(similarity, 3), "score": round(tfidf_score, config.SCORE_DECIMALS)},
        "format_penalty": penalty,
        "matched": [item for item in must + nice if item["matched"]],
        "missing_must_have": sorted((i for i in must if not i["matched"]), key=lambda i: -i["weight"]),
        "missing_nice_to_have": [item for item in nice if not item["matched"]],
        "ignored": ignored,
        "detected_skills": sorted(catalog.display(skill) for skill in found),
    }

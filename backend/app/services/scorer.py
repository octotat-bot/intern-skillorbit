"""Deterministic, rule-based resume scorer (/100).

Six parameters, weighted in ``config.SCORE_WEIGHTS``. Each parameter is a list
of checks; every check reports its points, maximum, status and the evidence
that produced it, so each point in the total can be traced. No LLM is involved.
"""

from __future__ import annotations

import re
from typing import Any

from app import config
from app.services import resume_features as features
from app.services.nlp import get_nlp
from app.services.skills import get_skill_matcher

Check = dict[str, Any]
Parameter = dict[str, Any]

PARAMETER_LABELS: dict[str, str] = {
    "contact": "Contact information",
    "structure": "Structure & sections",
    "skills": "Skills",
    "projects": "Projects",
    "education": "Education",
    "quality": "Writing quality",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _round(value: float) -> float:
    return round(value, config.SCORE_DECIMALS)


def _scaled(max_points: int, fraction: float) -> float:
    """``max_points`` times ``fraction`` clamped to [0, 1], rounded."""
    return _round(max_points * min(1.0, max(0.0, fraction)))


def _check(check_id: str, label: str, points: float, max_points: int, detail: str) -> Check:
    """One scored check with its evidence."""
    points = _round(points)
    status = "pass" if points >= max_points else "fail" if points <= 0 else "partial"
    return {"id": check_id, "label": label, "points": points, "max": max_points,
            "status": status, "detail": detail}


def _parameter(name: str, checks: list[Check]) -> Parameter:
    return {
        "label": PARAMETER_LABELS[name],
        "score": _round(sum(c["points"] for c in checks)),
        "max": config.SCORE_WEIGHTS[name],
        "evidence": checks,
    }


def _has(sections: dict[str, str], name: str) -> bool:
    return bool(sections.get(name, "").strip())


def _band(total: int) -> str:
    return next(label for minimum, label in config.SCORE_BANDS if total >= minimum)


def _range_fraction(value: int, low: int, high: int) -> float:
    """1.0 inside [low, high]; proportionally less below or above."""
    if value <= 0:
        return 0.0
    if value < low:
        return value / low
    if value > high:
        return high / value
    return 1.0


def _quote(items: list[str], limit: int = 3) -> str:
    shown = ", ".join(f"'{item}'" for item in items[:limit])
    return shown + (f" (+{len(items) - limit} more)" if len(items) > limit else "")


# ---------------------------------------------------------------------------
# Contact (10)
# ---------------------------------------------------------------------------
def score_contact(contact: dict[str, Any]) -> Parameter:
    """Email, phone, LinkedIn and GitHub presence."""
    specs = [
        ("email", "Email address", config.CONTACT_EMAIL_POINTS),
        ("phone", "Phone number", config.CONTACT_PHONE_POINTS),
        ("linkedin", "LinkedIn profile", config.CONTACT_LINKEDIN_POINTS),
        ("github", "GitHub profile", config.CONTACT_GITHUB_POINTS),
    ]
    checks = [
        _check(f"contact.{key}", label, points if contact.get(key) else 0, points,
               f"Found: {contact[key]}" if contact.get(key) else "Not found")
        for key, label, points in specs
    ]
    return _parameter("contact", checks)


# ---------------------------------------------------------------------------
# Structure (20)
# ---------------------------------------------------------------------------
def score_structure(sections: dict[str, str]) -> Parameter:
    """Required sections present with content, and a sensible order."""
    checks = [
        _check(f"structure.{name}", f"{name.capitalize()} section",
               config.SECTION_PRESENT_POINTS if _has(sections, name) else 0,
               config.SECTION_PRESENT_POINTS,
               "Present" if _has(sections, name)
               else "Heading found but empty" if name in sections else "Missing")
        for name in config.REQUIRED_SECTIONS
    ]
    return _parameter("structure", checks + _order_checks(sections))


def _order_checks(sections: dict[str, str]) -> list[Check]:
    """Three ordering rules. Order is only judged with enough core sections."""
    order = [name for name in sections if _has(sections, name)]
    position = {name: index for index, name in enumerate(order)}
    core = [position[s] for s in config.CORE_SECTIONS if s in position]
    supporting = [position[s] for s in config.SUPPORTING_SECTIONS if s in position]
    points = config.SECTION_ORDER_POINTS
    if len(core) < config.MIN_CORE_SECTIONS_FOR_ORDER:
        detail = f"Only {len(core)} core section(s); order cannot be judged"
        return [_check(f"structure.order.{rule}", label, 0, points[rule], detail)
                for rule, label in _ORDER_RULE_LABELS.items()]

    contact_first = bool(order) and order[0] == "contact"
    summary_ok = "summary" not in position or position["summary"] < min(core)
    supporting_ok = not supporting or max(core) < min(supporting)
    sequence = " > ".join(order)
    return [
        _check("structure.order.contact_first", _ORDER_RULE_LABELS["contact_first"],
               points["contact_first"] if contact_first else 0, points["contact_first"],
               f"Order: {sequence}"),
        _check("structure.order.summary_before_core", _ORDER_RULE_LABELS["summary_before_core"],
               points["summary_before_core"] if summary_ok else 0, points["summary_before_core"],
               "No summary (rule not applicable)" if "summary" not in position else f"Order: {sequence}"),
        _check("structure.order.core_before_supporting", _ORDER_RULE_LABELS["core_before_supporting"],
               points["core_before_supporting"] if supporting_ok else 0, points["core_before_supporting"],
               "No certifications/achievements (rule not applicable)" if not supporting else f"Order: {sequence}"),
    ]


_ORDER_RULE_LABELS: dict[str, str] = {
    "contact_first": "Contact details at the top",
    "summary_before_core": "Summary before main sections",
    "core_before_supporting": "Certifications/achievements after main sections",
}


# ---------------------------------------------------------------------------
# Skills (20)
# ---------------------------------------------------------------------------
def score_skills(sections: dict[str, str]) -> Parameter:
    """Skills section exists, is categorised, and lists a sane number of skills."""
    text = sections.get("skills", "")
    exists = bool(text.strip())
    categories = features.skill_categories(text)
    items = features.skill_items(text)
    recognised = sorted(get_skill_matcher().find_skills(text))
    count = max(len(items), len(recognised))
    categorised = len(categories) >= config.SKILLS_MIN_CATEGORIES
    fraction = _range_fraction(count, config.MIN_SKILLS_COUNT, config.MAX_SKILLS_COUNT)
    checks = [
        _check("skills.section", "Skills section present",
               config.SKILLS_SECTION_EXISTS_POINTS if exists else 0, config.SKILLS_SECTION_EXISTS_POINTS,
               "Present" if exists else "No skills section found"),
        _check("skills.categorized", "Skills grouped into categories",
               config.SKILLS_CATEGORIZED_POINTS if categorised else 0, config.SKILLS_CATEGORIZED_POINTS,
               f"{len(categories)} categories: {_quote(categories)}" if categories
               else f"No 'Category: skills' lines (need {config.SKILLS_MIN_CATEGORIES})"),
        _check("skills.count", "Number of skills listed",
               _scaled(config.SKILLS_COUNT_POINTS, fraction), config.SKILLS_COUNT_POINTS,
               f"{count} skills listed (ideal {config.MIN_SKILLS_COUNT}-{config.MAX_SKILLS_COUNT})"
               + (f": {_quote(items)}" if items else "")),
    ]
    return _parameter("skills", checks)


# ---------------------------------------------------------------------------
# Projects (20)
# ---------------------------------------------------------------------------
def score_projects(sections: dict[str, str]) -> Parameter:
    """Project count, technology named per project, action verbs, quantified impact."""
    projects = features.split_entries(sections.get("projects", ""))
    count = len(projects)
    lines = [line for project in projects for line in project.lines]
    matcher = get_skill_matcher()
    with_tech = [p for p in projects if matcher.find_skills(p.text)]
    strong = [line for line in lines if (verb := features.leading_verb(line)) and verb.strength == "strong"]
    quantified = [p for p in projects if any(features.find_metrics(line) for line in p.lines)]
    names = [p.title or p.lines[0][:40] for p in projects]

    def share(part: list, whole: list) -> float:
        return len(part) / len(whole) if whole else 0.0

    checks = [
        _check("projects.count", "Number of projects",
               _scaled(config.PROJECT_COUNT_POINTS, count / config.IDEAL_PROJECT_COUNT_MIN),
               config.PROJECT_COUNT_POINTS,
               f"{count} project(s) (ideal {config.IDEAL_PROJECT_COUNT_MIN}-{config.IDEAL_PROJECT_COUNT_MAX})"
               + (f": {_quote(names)}" if names else "")),
        _check("projects.tech", "Technologies named per project",
               _scaled(config.PROJECT_TECH_NAMED_POINTS, share(with_tech, projects)),
               config.PROJECT_TECH_NAMED_POINTS,
               f"{len(with_tech)}/{count} projects name a technology"),
        _check("projects.action_verbs", "Bullets start with action verbs",
               _scaled(config.PROJECT_ACTION_VERB_POINTS, share(strong, lines)),
               config.PROJECT_ACTION_VERB_POINTS,
               f"{len(strong)}/{len(lines)} description lines start with a strong verb"),
        _check("projects.quantified", "Quantified impact",
               _scaled(config.PROJECT_QUANTIFIED_POINTS, share(quantified, projects)),
               config.PROJECT_QUANTIFIED_POINTS,
               f"{len(quantified)}/{count} projects include a number or metric"),
    ]
    return _parameter("projects", checks)


# ---------------------------------------------------------------------------
# Education (10)
# ---------------------------------------------------------------------------
_DEGREE_RE = re.compile(r"\b(?:" + "|".join(map(re.escape, config.DEGREE_TERMS)) + r")\b")
_DEGREE_ABBR_RE = re.compile(
    r"(?<![A-Za-z])(?:" + "|".join(map(re.escape, config.DEGREE_ABBREVIATIONS)) + r")(?![A-Za-z])"
)
_INSTITUTION_RE = re.compile(r"\b(?:" + "|".join(config.INSTITUTION_KEYWORDS) + r")\b", re.I)
_EDU_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b|\b(?:present|expected|pursuing|ongoing)\b", re.I)


def find_degree(text: str) -> str | None:
    """A degree name such as 'B.Tech' or 'Bachelor', or None."""
    flattened = re.sub(r"[.\s]+", " ", text.lower())
    match = _DEGREE_RE.search(flattened) or _DEGREE_ABBR_RE.search(text)
    return match.group(0).strip() if match else None


def find_institution(text: str) -> str | None:
    """An institution keyword match, falling back to a spaCy ORG entity."""
    match = _INSTITUTION_RE.search(text)
    if match:
        line = next(line for line in text.split("\n") if match.group(0) in line)
        return line.strip()
    orgs = [ent.text for ent in get_nlp()(text).ents if ent.label_ == "ORG"]
    return orgs[0] if orgs else None


def score_education(sections: dict[str, str]) -> Parameter:
    """Degree, institution and year present in the education section."""
    text = sections.get("education", "")
    degree = find_degree(text) if text else None
    institution = find_institution(text) if text else None
    year = _EDU_YEAR_RE.search(text) if text else None
    missing = "No education section" if not text.strip() else "Not found"
    checks = [
        _check("education.degree", "Degree", config.EDUCATION_DEGREE_POINTS if degree else 0,
               config.EDUCATION_DEGREE_POINTS, f"Found: {degree}" if degree else missing),
        _check("education.institution", "Institution", config.EDUCATION_INSTITUTION_POINTS if institution else 0,
               config.EDUCATION_INSTITUTION_POINTS, f"Found: {institution}" if institution else missing),
        _check("education.year", "Graduation year", config.EDUCATION_YEAR_POINTS if year else 0,
               config.EDUCATION_YEAR_POINTS, f"Found: {year.group(0)}" if year else missing),
    ]
    return _parameter("education", checks)


# ---------------------------------------------------------------------------
# Quality / completeness (20)
# ---------------------------------------------------------------------------
def _tiered(max_points: int, hits: int, partial_max: int) -> float:
    """Full points for zero hits, half up to ``partial_max``, otherwise zero."""
    if hits == 0:
        return max_points
    return max_points / 2 if hits <= partial_max else 0


def score_quality(sections: dict[str, str], stats: dict[str, Any]) -> Parameter:
    """Length, verb strength, first person, filler and formatting consistency."""
    words = stats.get("word_count", 0)
    if words == 0:
        return _parameter("quality", _empty_quality_checks())

    body = "\n".join(text for name, text in sections.items() if name != "contact")
    bullet_lines = [line for name in ("experience", "projects")
                    for line in features.description_lines(sections.get(name, ""))]
    verbs = [v for line in bullet_lines if (v := features.leading_verb(line))]
    strong = [v.word for v in verbs if v.strength == "strong"]
    weak = [v.word for v in verbs if v.strength == "weak"]
    pronouns = features.first_person_hits(body)
    filler = features.filler_hits(body)
    bullet_styles = stats.get("bullet_styles", [])
    dates = features.date_styles(body)

    checks = [
        _check("quality.length", "Resume length",
               _scaled(config.QUALITY_LENGTH_POINTS,
                       _range_fraction(words, config.MIN_RESUME_WORDS, config.MAX_RESUME_WORDS)),
               config.QUALITY_LENGTH_POINTS,
               f"{words} words (ideal {config.MIN_RESUME_WORDS}-{config.MAX_RESUME_WORDS})"),
        _check("quality.verb_strength", "Strong action verbs",
               _scaled(config.QUALITY_VERB_STRENGTH_POINTS, len(strong) / len(verbs)) if verbs else 0,
               config.QUALITY_VERB_STRENGTH_POINTS,
               f"{len(strong)} strong, {len(weak)} weak" + (f"; weak: {_quote(weak)}" if weak else "")
               if verbs else "No experience/project bullets start with a verb"),
        _check("quality.first_person", "No first-person pronouns",
               _tiered(config.QUALITY_NO_FIRST_PERSON_POINTS, len(pronouns), config.FIRST_PERSON_PARTIAL_MAX),
               config.QUALITY_NO_FIRST_PERSON_POINTS,
               f"{len(pronouns)} found: {_quote(pronouns)}" if pronouns else "None found"),
        _check("quality.filler", "No filler phrases",
               _tiered(config.QUALITY_NO_FILLER_POINTS, len(filler), config.FILLER_PARTIAL_MAX),
               config.QUALITY_NO_FILLER_POINTS,
               f"{len(filler)} found: {_quote(filler)}" if filler else "None found"),
        _check("quality.bullet_consistency", "Consistent bullet style",
               config.QUALITY_BULLET_CONSISTENCY_POINTS if len(bullet_styles) <= 1 else 0,
               config.QUALITY_BULLET_CONSISTENCY_POINTS,
               f"Bullet styles: {' '.join(bullet_styles)}" if bullet_styles else "No bullets used"),
        _check("quality.date_consistency", "Consistent date format",
               config.QUALITY_DATE_CONSISTENCY_POINTS if len(dates) <= 1 else 0,
               config.QUALITY_DATE_CONSISTENCY_POINTS,
               "; ".join(f"{style} e.g. '{example}'" for style, example in dates.items())
               if dates else "No month-level dates found"),
    ]
    return _parameter("quality", checks)


def _empty_quality_checks() -> list[Check]:
    """Quality checks for a resume with no extractable text: nothing can be credited."""
    specs = [
        ("quality.length", "Resume length", config.QUALITY_LENGTH_POINTS),
        ("quality.verb_strength", "Strong action verbs", config.QUALITY_VERB_STRENGTH_POINTS),
        ("quality.first_person", "No first-person pronouns", config.QUALITY_NO_FIRST_PERSON_POINTS),
        ("quality.filler", "No filler phrases", config.QUALITY_NO_FILLER_POINTS),
        ("quality.bullet_consistency", "Consistent bullet style", config.QUALITY_BULLET_CONSISTENCY_POINTS),
        ("quality.date_consistency", "Consistent date format", config.QUALITY_DATE_CONSISTENCY_POINTS),
    ]
    return [_check(cid, label, 0, points, "No text could be extracted") for cid, label, points in specs]


# ---------------------------------------------------------------------------
# Total
# ---------------------------------------------------------------------------
def score_resume(sections: dict[str, str], contact: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
    """Score a parsed resume deterministically.

    Args:
        sections: ``{section: text}`` from the parser.
        contact: Contact details from the parser.
        stats: Text statistics from the parser (word count, bullet styles).

    Returns:
        ``{total, max, band, parameters: {name: {label, score, max, evidence[]}}}``.
    """
    parameters = {
        "contact": score_contact(contact),
        "structure": score_structure(sections),
        "skills": score_skills(sections),
        "projects": score_projects(sections),
        "education": score_education(sections),
        "quality": score_quality(sections, stats),
    }
    total = int(round(sum(p["score"] for p in parameters.values())))
    return {"total": total, "max": 100, "band": _band(total), "parameters": parameters}

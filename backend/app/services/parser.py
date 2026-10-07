"""Resume parsing service.

Pipeline: extract text -> normalise -> detect sections -> extract contact
details -> assess parse quality. Every step is deterministic, so the same file
always yields the same output.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from app import config
from app.services.extract import ExtractionResult, ParseError, extract
from app.services.nlp import get_nlp

__all__ = ["ParseError", "ParsedResume", "parse_resume"]


@dataclass
class ParsedResume:
    """Structured result of parsing one resume."""

    raw_text: str
    clean_text: str
    sections: dict[str, str]
    contact: dict[str, Any]
    parse_quality: dict[str, Any]
    stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict."""
        return asdict(self)


@dataclass
class NormalizedText:
    """Normalised text plus what was learned about bullets while cleaning."""

    text: str
    bullet_line_count: int
    bullet_styles: list[str]


def parse_resume(file_bytes: bytes, file_type: str) -> ParsedResume:
    """Parse an uploaded resume.

    Args:
        file_bytes: Raw file content.
        file_type: ``"pdf"`` or ``"docx"``.

    Returns:
        The parsed resume.

    Raises:
        ParseError: If the file cannot be read.
    """
    extraction = extract(file_bytes, file_type)
    normalized = normalize_text(extraction.text)
    sections = detect_sections(normalized.text)
    contact = extract_contact(normalized.text, extraction.links, sections.get("contact", ""))
    stats = compute_stats(normalized)
    quality = assess_parse_quality(normalized.text, sections, extraction, stats)
    return ParsedResume(
        raw_text=extraction.text,
        clean_text=normalized.text,
        sections=sections,
        contact=contact,
        parse_quality=quality,
        stats=stats,
    )


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
_UNICODE_BULLET_RE = re.compile(r"^([•●○◦▪▫■□►▸‣⁃∙·➢➤✓✔❖◆◇])\s*")
_ASCII_BULLET_RE = re.compile(r"^([-*–—>]|o(?=\s))\s+")
_INVISIBLE_RE = re.compile("[​-‏  ⁠﻿-]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_SPACES_RE = re.compile(r"[ \t]+")
_PUNCTUATION_MAP = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"', "′": "'",
})


def normalize_text(text: str) -> NormalizedText:
    """Clean extracted text and strip bullet glyphs.

    Applies Unicode NFKC (fixes ligatures and full-width characters), removes
    invisible, private-use and control characters, straightens quotes,
    collapses whitespace, strips bullets, and keeps at most one blank line in a row.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE_RE.sub("", text).translate(_PUNCTUATION_MAP)
    text = _CONTROL_RE.sub("", text)

    lines: list[str] = []
    styles: set[str] = set()
    bullet_lines = 0
    for raw_line in text.split("\n"):
        line, bullet = _strip_bullet(_SPACES_RE.sub(" ", raw_line).strip())
        if bullet:
            styles.add(bullet)
            bullet_lines += 1
        if line or (lines and lines[-1]):
            lines.append(line)
    return NormalizedText("\n".join(lines).strip(), bullet_lines, sorted(styles))


def _strip_bullet(line: str) -> tuple[str, str | None]:
    """Remove a leading bullet glyph, returning the text and the glyph found."""
    for pattern in (_UNICODE_BULLET_RE, _ASCII_BULLET_RE):
        match = pattern.match(line)
        if match:
            return line[match.end():].strip(), match.group(1)
    return line, None


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------
def _heading_key(text: str) -> str:
    """Normalise a candidate heading: lowercase, '&' -> 'and', letters only."""
    text = text.lower().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z ]+", " ", text).split())


_ALIAS_TO_SECTION: dict[str, str] = {
    _heading_key(alias): section
    for section, aliases in config.SECTION_HEADINGS.items()
    for alias in aliases
}
_INLINE_HEADING_RE = re.compile(r"^([A-Za-z][A-Za-z &/]{2,40}?)\s*:\s*(\S.*)$")


def _keyword_section(key: str) -> str | None:
    """Map a heading key to a section via keyword stems, scanning words left to right."""
    for word in key.split():
        for stem, section in config.SECTION_KEYWORDS.items():
            if word.startswith(stem):
                return section
    return None


def match_heading(line: str) -> tuple[str, str] | None:
    """Decide whether a line is a section heading.

    Three rules, tried in order:
      1. Inline heading: ``"Skills: Python, SQL"``. Only for aliases that contain
         a section keyword, so sub-labels like ``"Languages: Python"`` stay in
         their section.
      2. Exact alias in any case: ``"Work Experience"``, ``"EDUCATION:"``.
      3. Unknown ALL-CAPS or colon-terminated short line containing a section
         keyword: ``"TECHNICAL SKILLS & TOOLS"``.

    Returns:
        ``(section, inline_content)`` or None when the line is body text.
    """
    stripped = line.strip()
    inline = _INLINE_HEADING_RE.match(stripped)
    if inline:
        key = _heading_key(inline.group(1))
        section = _ALIAS_TO_SECTION.get(key)
        if section and section != "other" and _keyword_section(key) == section:
            return section, inline.group(2).strip()

    words = stripped.split()
    if not words or len(words) > config.MAX_HEADING_WORDS:
        return None
    key = _heading_key(stripped)
    if key in _ALIAS_TO_SECTION:
        return _ALIAS_TO_SECTION[key], ""
    if _looks_like_keyword_heading(stripped, words):
        section = _keyword_section(key)
        if section:
            return section, ""
    return None


def _looks_like_keyword_heading(stripped: str, words: list[str]) -> bool:
    """ALL-CAPS or colon-terminated, short, no digits. Title Case is excluded so
    project titles such as 'Skill Matcher App' are not mistaken for headings."""
    return (
        len(words) <= config.MAX_KEYWORD_HEADING_WORDS
        and not any(ch.isdigit() for ch in stripped)
        and (stripped.isupper() or stripped.endswith(":"))
    )


def detect_sections(text: str) -> dict[str, str]:
    """Split normalised text into ``{section: text}`` in document order.

    Text before the first heading is the ``contact`` block. Repeated headings
    for the same section are merged. A heading with no body still appears,
    with empty text, so callers know the section exists.
    """
    collected: dict[str, list[str]] = {}
    current = "contact"
    for line in text.split("\n"):
        heading = match_heading(line)
        if heading:
            current, inline = heading
            collected.setdefault(current, [])
            if inline:
                collected[current].append(inline)
        elif line.strip():
            collected.setdefault(current, []).append(line)
    return {name: "\n".join(lines) for name, lines in collected.items()}


def detected_section_names(sections: dict[str, str]) -> list[str]:
    """Section names to report to clients (excludes the unscored 'other' bucket)."""
    return [name for name in sections if name != "other"]


# ---------------------------------------------------------------------------
# Contact details
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\w/.(])(\+?\(?\d[\d\s().-]{7,20}\d)(?![\w/])")
_YEAR_RE = re.compile(r"(?:19|20)\d\d")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_%-]+/?", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", re.I)
_NAME_PREFIX_RE = re.compile(r"^name\s*[:\-]\s*", re.I)
_NAME_WORD_RE = re.compile(r"^[A-Z][A-Za-z.'-]*$")


def extract_contact(text: str, links: list[str], header: str) -> dict[str, Any]:
    """Extract email, phone, LinkedIn, GitHub and a best-guess name.

    Hyperlink targets (e.g. a 'LinkedIn' label linking to a profile) are
    searched alongside the visible text. Missing values are ``None``.
    """
    haystack = "\n".join([text, *links])
    return {
        "email": _first_match(EMAIL_RE, haystack),
        "phone": find_phone(haystack),
        "linkedin": _first_match(LINKEDIN_RE, haystack),
        "github": _first_match(GITHUB_RE, haystack),
        **guess_name(header or text),
    }


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    """First match of ``pattern`` without trailing punctuation, or None."""
    match = pattern.search(text)
    return match.group(0).rstrip("/.,;") if match else None


def find_phone(text: str) -> str | None:
    """Return the first phone-like number with a plausible digit count.

    Date ranges match the pattern too. '2021 - 2025' has too few digits, and
    longer runs such as '2019 - 2023 2020' are rejected because every digit
    group is a year.
    """
    for match in PHONE_RE.finditer(text):
        candidate = match.group(1).strip()
        digits = sum(ch.isdigit() for ch in candidate)
        if config.PHONE_MIN_DIGITS <= digits <= config.PHONE_MAX_DIGITS and not _only_years(candidate):
            return candidate
    return None


def _only_years(candidate: str) -> bool:
    """True when every digit group is a four-digit year such as 2021."""
    return all(_YEAR_RE.fullmatch(group) for group in re.findall(r"\d+", candidate))


def guess_name(header: str) -> dict[str, str | None]:
    """Guess the candidate's name from the top lines of the resume.

    Tries spaCy PERSON entities first, then a heuristic of 2-4 capitalised
    alphabetic words. Returns ``{"name", "name_source"}``.
    """
    candidates = _name_candidates(header)
    nlp = get_nlp()
    for candidate in candidates:
        for ent in nlp(candidate).ents:
            if ent.label_ == "PERSON" and len(ent.text.split()) >= config.NAME_MIN_WORDS:
                return {"name": ent.text, "name_source": "spacy"}
    for candidate in candidates:
        if all(_NAME_WORD_RE.match(word) for word in candidate.split()):
            return {"name": candidate, "name_source": "heuristic"}
    return {"name": None, "name_source": None}


def _name_candidates(header: str) -> list[str]:
    """Top lines that could be a name, with 'Name:' prefixes and '| title' suffixes removed."""
    candidates: list[str] = []
    lines = [line for line in header.split("\n") if line.strip()][: config.NAME_SCAN_LINES]
    for line in lines:
        part = _NAME_PREFIX_RE.sub("", re.split(r"[|,]", line)[0]).strip()
        if _is_name_shaped(part):
            candidates.append(part.title() if part.isupper() else part)
    return candidates


def _is_name_shaped(text: str) -> bool:
    """2-4 words, no digits, emails, URLs or section headings."""
    words = text.split()
    return (
        config.NAME_MIN_WORDS <= len(words) <= config.NAME_MAX_WORDS
        and not any(ch.isdigit() or ch in "@/:" for ch in text)
        and _heading_key(text) not in _ALIAS_TO_SECTION
    )


# ---------------------------------------------------------------------------
# Statistics and parse quality
# ---------------------------------------------------------------------------
def compute_stats(normalized: NormalizedText) -> dict[str, Any]:
    """Word, line and bullet counts used by later scoring stages."""
    lines = [line for line in normalized.text.split("\n") if line.strip()]
    return {
        "word_count": len(normalized.text.split()),
        "line_count": len(lines),
        "bullet_line_count": normalized.bullet_line_count,
        "bullet_styles": normalized.bullet_styles,
    }


def _line_ratios(text: str) -> tuple[float, float]:
    """Share of lines that are very short, and share starting with a lowercase letter."""
    lines = [line for line in text.split("\n") if line.strip()]
    if not lines:
        return 0.0, 0.0
    short = sum(len(line) < config.SCRAMBLE_SHORT_LINE_THRESHOLD for line in lines)
    lowercase = sum(line[0].islower() for line in lines)
    return round(short / len(lines), 3), round(lowercase / len(lines), 3)


def _quality_metrics(
    text: str, sections: dict[str, str], extraction: ExtractionResult, stats: dict[str, Any]
) -> dict[str, Any]:
    """Collect the raw measurements the quality checks are based on."""
    short_ratio, lowercase_ratio = _line_ratios(text)
    return {
        "char_count": len(text),
        "word_count": stats["word_count"],
        "line_count": stats["line_count"],
        "page_count": extraction.page_count,
        "sections_found": len([s for s in sections if s not in ("contact", "other")]),
        "short_line_ratio": short_ratio,
        "lowercase_start_ratio": lowercase_ratio,
        "multi_column_pages": extraction.multi_column_pages,
        "table_count": extraction.table_count,
        "image_count": extraction.image_count,
        "extractor": extraction.extractor,
    }


def _issue(code: str, message: str, evidence: str) -> dict[str, Any]:
    """Build one parse-quality issue with its configured severity."""
    spec = config.PARSE_ISSUES[code]
    return {"code": code, "severity": spec["severity"], "message": message, "evidence": evidence}


def _quality_issues(m: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn metrics into ATS formatting-risk issues, each with its evidence."""
    issues: list[dict[str, Any]] = []
    non_extractable = m["char_count"] < config.MIN_TEXT_LENGTH
    if non_extractable:
        cause = "it appears to be a scanned image" if m["image_count"] else "it contains almost no text"
        issues.append(_issue(
            "non_extractable",
            f"Text could not be extracted because {cause}. ATS software cannot read it.",
            f"{m['char_count']} characters extracted; {m['image_count']} image(s) found.",
        ))
    elif m["word_count"] < config.PARSE_MIN_WORDS:
        issues.append(_issue(
            "too_short", "Very little text was extracted; the resume looks incomplete.",
            f"{m['word_count']} words extracted (minimum {config.PARSE_MIN_WORDS}).",
        ))
    if m["multi_column_pages"]:
        pages = ", ".join(map(str, m["multi_column_pages"]))
        issues.append(_issue(
            "multi_column",
            "A multi-column layout was detected. Many ATS read straight across columns, which scrambles content.",
            f"Two-column layout on page(s) {pages}.",
        ))
    if m["table_count"]:
        issues.append(_issue(
            "tables", "Tables were found. Some ATS skip or reorder table content.",
            f"{m['table_count']} table(s) found.",
        ))
    if not non_extractable and m["sections_found"] < config.MIN_SECTIONS_FOR_GOOD_PARSE:
        issues.append(_issue(
            "few_sections", "Few standard section headings were recognised.",
            f"{m['sections_found']} scored section(s) found (expected at least {config.MIN_SECTIONS_FOR_GOOD_PARSE}).",
        ))
    if m["line_count"] >= config.SCRAMBLE_MIN_LINES and (
        m["short_line_ratio"] > config.SCRAMBLE_SHORT_LINE_RATIO
        or m["lowercase_start_ratio"] > config.SCRAMBLE_LOWERCASE_START_RATIO
    ):
        issues.append(_issue(
            "fragmented_text",
            "Extracted text is fragmented, a sign of text boxes, columns or unusual formatting.",
            f"{m['short_line_ratio']:.0%} of lines are very short; "
            f"{m['lowercase_start_ratio']:.0%} start mid-sentence.",
        ))
    if (m["page_count"] or 0) > config.PARSE_MAX_PAGES or m["word_count"] > config.PARSE_MAX_WORDS:
        issues.append(_issue(
            "too_long", "The document is longer than a typical student resume.",
            f"{m['page_count'] or 'n/a'} page(s), {m['word_count']} words.",
        ))
    if m["image_count"] and not non_extractable:
        issues.append(_issue(
            "images", "Images or graphics were found. ATS ignore them, so do not put information in images.",
            f"{m['image_count']} image(s) found.",
        ))
    return issues


def _quality_level(score: int) -> str:
    """Map a 0-100 parse-quality score to good, fair or poor."""
    for level, threshold in config.PARSE_QUALITY_LEVELS.items():
        if score >= threshold:
            return level
    return "poor"


def assess_parse_quality(
    text: str, sections: dict[str, str], extraction: ExtractionResult, stats: dict[str, Any]
) -> dict[str, Any]:
    """Score how reliably the resume could be read, as an ATS formatting-risk signal.

    Returns:
        ``{score, level, ats_risk, issues[], metrics}`` where score starts at
        100 and each issue deducts its configured penalty.
    """
    metrics = _quality_metrics(text, sections, extraction, stats)
    issues = _quality_issues(metrics)
    penalty = sum(int(config.PARSE_ISSUES[i["code"]]["penalty"]) for i in issues)
    score = max(0, 100 - penalty)
    level = _quality_level(score)
    return {
        "score": score,
        "level": level,
        "ats_risk": level != "good",
        "issues": issues,
        "metrics": metrics,
    }

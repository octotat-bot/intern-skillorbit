"""Deterministic text features shared by the scorer and the feedback engine.

Everything here is pure string logic driven by word lists in ``config``:
verb strength, title-vs-description lines, project/experience entries,
quantified metrics, first-person pronouns, filler phrases, date styles and
skill-list items.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from app import config

# ---------------------------------------------------------------------------
# Verbs
# ---------------------------------------------------------------------------
_DOUBLING_RE = re.compile(r"[^aeiou][aeiou][bdglmnprt]$")   # program -> programmed
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
_LEADING_PRONOUNS = {"i", "we"}


def _inflections(base: str) -> set[str]:
    """Generate the common inflected forms of an English verb.

    Over-generation ("developes") is harmless because only real words appear
    in resumes. Noun-like verbs keep only past-tense and -ing forms.
    """
    past = {base + "ed", base + "d"} if base.endswith("e") else {base + "ed"}
    ing = {base[:-1] + "ing"} if base.endswith("e") else {base + "ing"}
    present = {base, base + "s", base + "es"}
    if base.endswith("y") and base[-2:-1] not in set("aeiou"):
        past.add(base[:-1] + "ied")
        present.add(base[:-1] + "ies")
    if _DOUBLING_RE.search(base):
        past.add(base + base[-1] + "ed")
        ing.add(base + base[-1] + "ing")
    past.update(config.IRREGULAR_VERB_FORMS.get(base, []))
    forms = past | ing if base in config.NOUN_LIKE_VERBS else past | ing | present
    british = {form.replace("iz", "is") for form in forms if "iz" in form}
    return forms | british


@lru_cache(maxsize=1)
def _verb_forms() -> tuple[dict[str, str], dict[str, str]]:
    """Inflected form -> base form, for strong and weak verbs."""
    strong = {form: base for base in config.STRONG_ACTION_VERBS for form in _inflections(base)}
    weak = {form: base for base in config.WEAK_VERBS for form in _inflections(base)}
    return strong, weak


@dataclass(frozen=True)
class LeadingVerb:
    """The verb a line opens with and whether it is strong or weak."""

    strength: str   # "strong" | "weak"
    word: str


def leading_verb(line: str) -> LeadingVerb | None:
    """Classify the verb that opens a line, skipping a leading 'I'/'We'.

    Weak phrases ("Responsible for") are checked first, then weak verbs, then
    strong verbs. Returns None when the line does not open with a known verb.
    """
    words = _WORD_RE.findall(line)
    if words and words[0].lower() in _LEADING_PRONOUNS:
        words = words[1:]
    if not words:
        return None
    opening = " ".join(words).lower()
    for phrase in config.WEAK_PHRASES:
        if opening.startswith(phrase):
            return LeadingVerb("weak", phrase)
    first = words[0].lower()
    strong, weak = _verb_forms()
    if first in weak:
        return LeadingVerb("weak", words[0])
    if first in strong:
        return LeadingVerb("strong", words[0])
    return None


# ---------------------------------------------------------------------------
# Lines and entries
# ---------------------------------------------------------------------------
_LABEL_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z /&+.-]{1,25}:\s*\S")


def lines_of(text: str) -> list[str]:
    """Non-empty, stripped lines."""
    return [line.strip() for line in text.split("\n") if line.strip()]


def is_description_line(line: str) -> bool:
    """True for bullet-like content lines, False for entry titles.

    Titles look like "Churn Prediction | Python, Pandas" or "Intern, Acme |
    2024". Descriptions open with a verb or pronoun, are 'Label: value'
    details, end with a period, or are long.
    """
    if leading_verb(line) or _LABEL_LINE_RE.match(line):
        return True
    first = _WORD_RE.match(line)
    if first and first.group(0).lower() in _LEADING_PRONOUNS:
        return True
    if " | " in line:
        return False
    return line.endswith(".") or len(line.split()) >= config.DESCRIPTION_MIN_WORDS


@dataclass
class Entry:
    """One project or job: a title line plus its description lines."""

    title: str
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Title and description as one block of text."""
        return "\n".join([self.title, *self.lines]).strip()


def split_entries(section_text: str) -> list[Entry]:
    """Group a projects/experience section into entries.

    Each title line starts a new entry; following description lines attach to
    it. Descriptions before any title form an untitled entry.
    """
    entries: list[Entry] = []
    for line in lines_of(section_text):
        if not is_description_line(line):
            entries.append(Entry(title=line))
        elif entries:
            entries[-1].lines.append(line)
        else:
            entries.append(Entry(title="", lines=[line]))
    return entries


def description_lines(section_text: str) -> list[str]:
    """All description lines of a section."""
    return [line for entry in split_entries(section_text) for line in entry.lines]


# ---------------------------------------------------------------------------
# Metrics, pronouns, filler, dates
# ---------------------------------------------------------------------------
_NUMBER_RE = re.compile(r"(?<![A-Za-z\d.,])\$?\d+(?:,\d{3})*(?:\.\d+)?\s?(?:%|\+|[kKmMbBxX]\b)?")
_YEAR_RE = re.compile(r"(?:19|20)\d\d")


def find_metrics(line: str) -> list[str]:
    """Quantities that signal measurable impact: numbers that are not bare years.

    Numbers glued to letters ("EC2", "Python3") are ignored.
    """
    found = []
    for match in _NUMBER_RE.finditer(line):
        token = match.group(0).strip()
        if not _YEAR_RE.fullmatch(token):
            found.append(token)
    return found


_FIRST_PERSON_RE = re.compile(
    r"\bI\b(?!\.)|\b(?:" + "|".join(
        f"[{w[0].upper()}{w[0]}]{w[1:]}" for w in config.FIRST_PERSON_PRONOUNS if w != "I"
    ) + r")\b"
)


def first_person_hits(text: str) -> list[str]:
    """First-person pronouns. Upper-case 'I' only, so 'ME' (degree) is ignored."""
    return _FIRST_PERSON_RE.findall(text)


def filler_hits(text: str) -> list[str]:
    """Cliché filler phrases present in the text (each listed once)."""
    lowered = text.lower()
    return [phrase for phrase in config.FILLER_PHRASES if re.search(rf"\b{re.escape(phrase)}\b", lowered)]


_ABBR_MONTHS = "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"   # "May" is ambiguous
_FULL_MONTHS = "January|February|March|April|June|July|August|September|October|November|December"
DATE_STYLES: dict[str, re.Pattern[str]] = {
    "Mon YYYY": re.compile(rf"\b(?:{_ABBR_MONTHS})\.?\s*'?\d{{2,4}}\b"),
    "Month YYYY": re.compile(rf"\b(?:{_FULL_MONTHS})\s+\d{{4}}\b"),
    "MM/YYYY": re.compile(r"(?<![\d./])(?:0?[1-9]|1[0-2])/(?:19|20)\d{2}\b"),
    "YYYY-MM": re.compile(r"\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])\b"),
}


def date_styles(text: str) -> dict[str, str]:
    """Date formats used, mapped to the first example of each."""
    found: dict[str, str] = {}
    for style, pattern in DATE_STYLES.items():
        match = pattern.search(text)
        if match:
            found[style] = match.group(0)
    return found


# ---------------------------------------------------------------------------
# Skills section
# ---------------------------------------------------------------------------
_SKILL_LABEL_RE = re.compile(r"^([A-Za-z][A-Za-z /&+.-]{1,30}):\s*(\S.*)$")
_SKILL_SPLIT_RE = re.compile(r"\s*[,;|•·]\s*")


def skill_categories(skills_text: str) -> list[str]:
    """Labels of 'Category: items' lines, e.g. ['Languages', 'Tools']."""
    return [m.group(1).strip() for line in lines_of(skills_text) if (m := _SKILL_LABEL_RE.match(line))]


def skill_items(skills_text: str) -> list[str]:
    """Individual listed skills, de-duplicated case-insensitively, labels removed.

    Fragments longer than SKILL_ITEM_MAX_CHARS are sentences, not skills.
    """
    items: dict[str, str] = {}
    for line in lines_of(skills_text):
        label = _SKILL_LABEL_RE.match(line)
        body = label.group(2) if label else line
        for part in _SKILL_SPLIT_RE.split(body):
            part = part.strip(" .")
            if part and len(part) <= config.SKILL_ITEM_MAX_CHARS and not part.isdigit():
                items.setdefault(part.casefold(), part)
    return list(items.values())

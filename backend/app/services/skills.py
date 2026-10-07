"""Skill detection over free text.

Three deterministic strategies, unioned:

1. ``LOWER`` phrase match on the surface text: canonical names and aliases,
   case-insensitive ("ReactJS" -> react).
2. Lemma phrase match: nouns are reduced to their lemma on both sides, so
   inflected forms match ("dashboards" -> dashboard, "REST APIs" -> rest api).
   Verbs keep their surface form, so "excelled" never becomes Excel.
3. Boundary-aware regexes for ambiguous short names that must match exact
   case ("R", "C", "Go", "Excel"), rejecting "R&D", "C#", "C++" and "Excelled".
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc

from app.services.nlp import get_nlp
from app.services.roles import RoleCatalog, load_catalog

_LEMMA_POS = {"NOUN", "PROPN"}


@dataclass(frozen=True, order=True)
class SkillHit:
    """One occurrence of a known skill in a text."""

    start: int      # character offset in the analysed text
    end: int
    skill: str      # canonical skill name
    surface: str    # text as written in the resume


def _lemma_form(token) -> str:
    """Lower-cased lemma for nouns, lower-cased text for everything else."""
    return token.lemma_.lower() if token.pos_ in _LEMMA_POS else token.lower_


def _case_sensitive_pattern(term: str) -> re.Pattern[str]:
    """Exact-case term not glued to letters, digits or symbols like + # & / -.

    A trailing period is allowed only at a sentence end ("... in R."), not
    inside a token such as "R.js".
    """
    return re.compile(rf"(?<![\w+#&/.-]){re.escape(term)}(?![\w+#&/-]|\.\w)")


class SkillMatcher:
    """Finds canonical skills in text. Build once; ``find`` is deterministic."""

    def __init__(self, terms: dict[str, str], case_sensitive: dict[str, str]) -> None:
        """
        Args:
            terms: Surface form -> canonical skill, matched case-insensitively.
            case_sensitive: Exact surface form -> canonical skill.
        """
        self._nlp = get_nlp()
        self._lower = PhraseMatcher(self._nlp.vocab, attr="LOWER")
        self._lemma = PhraseMatcher(self._nlp.vocab, attr="ORTH")
        by_skill: dict[str, list[str]] = defaultdict(list)
        for surface, skill in sorted(terms.items()):
            by_skill[skill].append(surface)
        for skill, surfaces in by_skill.items():
            docs = list(self._nlp.pipe(surfaces))
            self._lower.add(skill, [self._nlp.make_doc(s) for s in surfaces])
            self._lemma.add(skill, [self._lemma_doc(doc) for doc in docs])
        self._exact = [
            (_case_sensitive_pattern(surface), skill)
            for surface, skill in sorted(case_sensitive.items())
        ]

    def _lemma_doc(self, doc: Doc) -> Doc:
        return Doc(self._nlp.vocab, words=[_lemma_form(token) for token in doc])

    def find(self, text: str) -> list[SkillHit]:
        """Return every skill occurrence in ``text``, sorted by position."""
        if not text.strip():
            return []
        doc = self._nlp(text)
        hits: set[SkillHit] = set()
        for matcher, target in ((self._lower, doc), (self._lemma, self._lemma_doc(doc))):
            for match_id, start, end in matcher(target):
                span = doc[start:end]
                skill = self._nlp.vocab.strings[match_id]
                hits.add(SkillHit(span.start_char, span.end_char, skill, span.text))
        for pattern, skill in self._exact:
            hits.update(SkillHit(m.start(), m.end(), skill, m.group(0)) for m in pattern.finditer(text))
        return sorted(hits)

    def find_skills(self, text: str) -> set[str]:
        """Distinct canonical skills present in ``text``."""
        return {hit.skill for hit in self.find(text)}


def build_matcher(catalog: RoleCatalog) -> SkillMatcher:
    """Matcher over the catalogue vocabulary and aliases.

    Canonical names of case-sensitive skills (e.g. "r", "go") are not added as
    case-insensitive terms, because lower-case "r" or "go" is not a skill.
    """
    exact_targets = set(catalog.case_sensitive_terms.values())
    terms = {skill: skill for skill in catalog.vocabulary() if skill not in exact_targets}
    terms.update(catalog.aliases())
    return SkillMatcher(terms, catalog.case_sensitive_terms)


@lru_cache(maxsize=1)
def get_skill_matcher() -> SkillMatcher:
    """Process-wide matcher built from roles.json."""
    return build_matcher(load_catalog())

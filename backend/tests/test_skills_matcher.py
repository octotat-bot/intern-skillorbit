"""Tests for the spaCy-based skill matcher."""

from __future__ import annotations

import pytest

from app.services.skills import SkillMatcher, get_skill_matcher


@pytest.fixture(scope="module")
def matcher():
    return get_skill_matcher()


@pytest.mark.parametrize("text, skill", [
    ("Built apps in JS", "javascript"),                    # alias
    ("Frontend in ReactJS", "react"),
    ("Experience with ML pipelines", "machine learning"),
    ("node.js, Express.js", "node.js"),                    # dotted name, lower case
    ("Deployed on K8s", "kubernetes"),
    ("Created PowerBI reports", "power bi"),               # spelling variant
    ("Used sklearn and scikit-learn", "scikit-learn"),     # hyphenated token sequence
    ("Set up CI/CD pipelines", "ci/cd"),
    ("Designed REST APIs", "rest api"),                    # plural via lemma
    ("Built 3 dashboards", "dashboard"),                   # plural via lemma
    ("Statistical analysis in R.", "r"),                   # sentence-final R
    ("Wrote services in Go and C", "go"),
])
def test_detects_skill(matcher, text: str, skill: str) -> None:
    assert skill in matcher.find_skills(text)


@pytest.mark.parametrize("text, absent", [
    ("Excelled in coursework", "excel"),         # verb, not the product
    ("Led R&D for a lab", "r"),
    ("Projects in C# and C++", "c"),             # C# and C++ are not C
    ("Go-to person for releases", "go"),
    ("take a rest and go home", "go"),           # lower-case ambiguous words
    ("JavaScript developer", "java"),            # token boundary
])
def test_avoids_false_positives(matcher, text: str, absent: str) -> None:
    assert absent not in matcher.find_skills(text)


def test_hits_carry_offsets_and_surface(matcher) -> None:
    text = "Skills: Python and PostgreSQL"
    hits = {hit.skill: hit for hit in matcher.find(text)}
    assert text[hits["python"].start:hits["python"].end] == "Python"
    assert hits["postgresql"].surface == "PostgreSQL"


def test_results_are_sorted_and_deterministic(matcher) -> None:
    text = "SQL, Python, Tableau, AWS, Docker, React"
    first = matcher.find(text)
    assert first == matcher.find(text) == sorted(first)


def test_empty_text(matcher) -> None:
    assert matcher.find("   ") == []


def test_custom_matcher_with_small_vocabulary() -> None:
    custom = SkillMatcher({"widget": "widget", "wdgt": "widget"}, {"W": "w"})
    assert custom.find_skills("Built widgets, a wdgt, and W.") == {"widget", "w"}

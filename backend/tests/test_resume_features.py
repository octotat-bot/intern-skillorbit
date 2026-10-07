"""Tests for shared text features: verbs, entries, metrics, pronouns, dates, skills."""

from __future__ import annotations

import pytest

from app.services import resume_features as f


@pytest.mark.parametrize("line, strength", [
    ("Developed a REST API", "strong"),
    ("Optimised SQL queries", "strong"),        # British spelling
    ("Programmed a robot arm", "strong"),       # consonant doubling
    ("Led a team of 5", "strong"),              # irregular past
    ("Engineered 25 features", "strong"),       # noun-like verb, past tense
    ("Helped the team ship", "weak"),
    ("Responsible for testing", "weak"),        # weak phrase
    ("I made a website", "weak"),               # leading pronoun skipped
    ("Worked on dashboards", "weak"),
])
def test_leading_verb(line: str, strength: str) -> None:
    verb = f.leading_verb(line)
    assert verb is not None and verb.strength == strength


@pytest.mark.parametrize("line", ["Engineer at Google", "Design Intern, Acme", "Research Assistant",
                                  "Customer Churn Prediction", ""])
def test_no_leading_verb(line: str) -> None:
    assert f.leading_verb(line) is None


@pytest.mark.parametrize("line, is_description", [
    ("Customer Churn Prediction | Python, Pandas", False),
    ("Data Analyst Intern, Flipkart | May 2024 - Jul 2024", False),
    ("Portfolio Website", False),
    ("Built a responsive site", True),
    ("Tech Stack: React, Node.js", True),
    ("A tool that predicts churn for telecom customers.", True),
    ("We shipped a mobile app", True),
])
def test_description_vs_title(line: str, is_description: bool) -> None:
    assert f.is_description_line(line) is is_description


def test_split_entries_groups_titles_and_bullets() -> None:
    text = "Churn Model | Python\nBuilt a model.\nCut churn 5%.\nPortfolio | React\nDesigned a site."
    entries = f.split_entries(text)
    assert [e.title for e in entries] == ["Churn Model | Python", "Portfolio | React"]
    assert entries[0].lines == ["Built a model.", "Cut churn 5%."]


def test_split_entries_untitled_leading_description() -> None:
    entries = f.split_entries("Made a website for a fest.")
    assert len(entries) == 1 and entries[0].title == ""


@pytest.mark.parametrize("line, metrics", [
    ("Cut costs by 40% for 10,000+ users", ["40%", "10,000+"]),
    ("Processed 2M+ rows, 3x faster, saved $5k", ["2M", "3x", "$5k"]),
    ("Deployed on EC2 in 2023, Jun 2023 - Aug 2024", []),   # glued digits and years
    ("Achieved 89.5% accuracy", ["89.5%"]),
])
def test_find_metrics(line: str, metrics: list[str]) -> None:
    assert f.find_metrics(line) == metrics


def test_first_person_hits() -> None:
    assert f.first_person_hits("I built my app. Me and myself.") == ["I", "my", "Me", "myself"]


@pytest.mark.parametrize("text", ["M.E. in Civil, ME 2020", "Used MySQL", "Phase I. complete", "Mine the data"])
def test_first_person_false_positives_avoided(text: str) -> None:
    hits = f.first_person_hits(text)
    assert "ME" not in hits and "I" not in hits


def test_filler_hits() -> None:
    assert f.filler_hits("A hard-working team player, passionate about AI") == ["team player", "passionate about"]


def test_date_styles() -> None:
    text = "May 2024 - Jul 2024; January 2023; 05/2022; CGPA 8.7/10; 2021-2025"
    assert f.date_styles(text) == {"Mon YYYY": "Jul 2024", "Month YYYY": "January 2023", "MM/YYYY": "05/2022"}


def test_skill_items_and_categories() -> None:
    text = ("Languages: Python, SQL, python\nTools: Git | Docker; Tableau\n"
            "Proficient in building scalable distributed systems with many tools")
    assert f.skill_categories(text) == ["Languages", "Tools"]
    assert f.skill_items(text) == ["Python", "SQL", "Git", "Docker", "Tableau"]

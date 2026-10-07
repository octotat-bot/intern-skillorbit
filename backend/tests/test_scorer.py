"""Tests for each scoring parameter and the total."""

from __future__ import annotations

import pytest

from app import config
from app.services.parser import parse_resume
from app.services.scorer import (
    score_contact,
    score_education,
    score_projects,
    score_quality,
    score_resume,
    score_skills,
    score_structure,
)


def _by_id(parameter: dict) -> dict:
    return {check["id"]: check for check in parameter["evidence"]}


def _score(parsed) -> dict:
    return score_resume(parsed.sections, parsed.contact, parsed.stats)


class TestContact:
    def test_all_present(self) -> None:
        contact = {"email": "a@b.co", "phone": "9876543210", "linkedin": "linkedin.com/in/a", "github": "github.com/a"}
        result = score_contact(contact)
        assert result["score"] == result["max"] == 10
        assert _by_id(result)["contact.email"]["detail"] == "Found: a@b.co"

    def test_only_email(self) -> None:
        result = score_contact({"email": "a@b.co"})
        assert result["score"] == config.CONTACT_EMAIL_POINTS
        assert _by_id(result)["contact.github"]["status"] == "fail"


class TestStructure:
    FULL = {"contact": "x", "summary": "s", "education": "e", "skills": "k",
            "experience": "w", "projects": "p", "certifications": "c"}

    def test_complete_and_ordered(self) -> None:
        assert score_structure(self.FULL)["score"] == 20

    def test_missing_and_empty_sections(self) -> None:
        sections = {"contact": "x", "education": "e", "skills": "", "projects": "p"}
        checks = _by_id(score_structure(sections))
        assert checks["structure.skills"]["detail"] == "Heading found but empty"
        assert checks["structure.experience"]["detail"] == "Missing"

    def test_bad_order_loses_order_points(self) -> None:
        sections = {"certifications": "c", "summary": "s", "skills": "k", "education": "e",
                    "experience": "w", "projects": "p"}
        checks = _by_id(score_structure(sections))
        assert checks["structure.order.contact_first"]["points"] == 0
        assert checks["structure.order.core_before_supporting"]["points"] == 0
        assert checks["structure.order.summary_before_core"]["status"] == "pass"

    def test_order_not_judged_with_too_few_sections(self) -> None:
        checks = _by_id(score_structure({"contact": "x", "skills": "k"}))
        assert checks["structure.order.contact_first"]["points"] == 0
        assert "cannot be judged" in checks["structure.order.contact_first"]["detail"]


class TestSkills:
    def test_categorised_list_scores_full(self) -> None:
        text = "Languages: Python, SQL, Java\nTools: Git, Docker, Tableau"
        assert score_skills({"skills": text})["score"] == 20

    def test_sparse_uncategorised(self) -> None:
        checks = _by_id(score_skills({"skills": "Python, MS Office"}))
        assert checks["skills.categorized"]["points"] == 0
        assert checks["skills.count"]["points"] == pytest.approx(config.SKILLS_COUNT_POINTS * 2 / config.MIN_SKILLS_COUNT)

    def test_overstuffed_list_is_penalised(self) -> None:
        text = ", ".join(f"Skill{i}" for i in range(60))
        assert _by_id(score_skills({"skills": text}))["skills.count"]["points"] == 5.0

    def test_missing_section(self) -> None:
        assert score_skills({})["score"] == 0


class TestProjects:
    STRONG = ("Churn Model | Python, Pandas\nEngineered 25 features reaching 89% accuracy.\n"
              "Sales Dashboard | SQL, Tableau\nBuilt a dashboard tracking 12 KPIs.\n"
              "Portfolio | React\nDesigned a site with a 95+ Lighthouse score.")

    def test_strong_projects_score_full(self) -> None:
        assert score_projects({"projects": self.STRONG})["score"] == 20

    def test_weak_project(self) -> None:
        checks = _by_id(score_projects({"projects": "I made a website for my college fest."}))
        assert checks["projects.count"]["points"] == 2.0
        assert checks["projects.tech"]["points"] == 0
        assert checks["projects.action_verbs"]["points"] == 0
        assert checks["projects.quantified"]["points"] == 0

    def test_partial_metrics(self) -> None:
        text = "A | Python\nBuilt X with 50% gain.\nB | SQL\nBuilt Y."
        assert _by_id(score_projects({"projects": text}))["projects.quantified"]["detail"].startswith("1/2")


class TestEducation:
    @pytest.mark.parametrize("text", [
        "B.Tech in CSE\nIIT Delhi | 2021 - 2025",
        "Bachelor of Science, University of Mumbai, Expected 2026",
        "B.E. Mechanical, Anna University, 2019",
    ])
    def test_complete(self, text: str) -> None:
        assert score_education({"education": text})["score"] == 10

    def test_degree_only(self) -> None:
        checks = _by_id(score_education({"education": "BSc Computer Science"}))
        assert checks["education.degree"]["status"] == "pass"
        assert checks["education.institution"]["status"] == "fail"
        assert checks["education.year"]["status"] == "fail"

    def test_missing_section(self) -> None:
        result = score_education({})
        assert result["score"] == 0
        assert _by_id(result)["education.degree"]["detail"] == "No education section"


class TestQuality:
    def test_clean_resume(self) -> None:
        sections = {"experience": "Intern, Acme | Jan 2024 - Mar 2024\nBuilt APIs.\nReduced cost 10%."}
        stats = {"word_count": 400, "bullet_styles": ["•"]}
        assert score_quality(sections, stats)["score"] == 20

    def test_problems_are_each_penalised(self) -> None:
        sections = {
            "summary": "I am a hard worker and team player. My goal is growth.",
            "experience": "Intern | Jan 2024 - March 2024\nHelped the team.\nWorked on tests.",
        }
        stats = {"word_count": 400, "bullet_styles": ["•", "-"]}
        checks = _by_id(score_quality(sections, stats))
        assert checks["quality.verb_strength"]["points"] == 0
        assert checks["quality.first_person"]["points"] == config.QUALITY_NO_FIRST_PERSON_POINTS / 2
        assert checks["quality.filler"]["points"] == 0
        assert checks["quality.bullet_consistency"]["points"] == 0
        assert checks["quality.date_consistency"]["points"] == 0
        assert checks["quality.length"]["status"] == "pass"

    def test_short_resume_gets_scaled_credit_for_absent_problems(self) -> None:
        sections = {"experience": "Intern | Jan 2024 - Mar 2024\nBuilt APIs."}
        checks = _by_id(score_quality(sections, {"word_count": 60, "bullet_styles": []}))
        coverage = 60 / config.MIN_RESUME_WORDS
        assert checks["quality.length"]["points"] == pytest.approx(5 * coverage, abs=0.1)
        assert checks["quality.first_person"]["points"] == pytest.approx(config.QUALITY_NO_FIRST_PERSON_POINTS * coverage, abs=0.1)
        assert checks["quality.filler"]["status"] == "partial"
        assert "only 60 words" in checks["quality.filler"]["detail"]

    def test_no_text_earns_nothing(self) -> None:
        assert score_quality({}, {"word_count": 0})["score"] == 0


class TestTotal:
    def test_good_resume_is_excellent(self, good_pdf) -> None:
        result = _score(parse_resume(good_pdf, "pdf"))
        assert result["total"] == 100 and result["band"] == "Excellent"

    def test_weak_resume_needs_work(self, weak_docx) -> None:
        result = _score(parse_resume(weak_docx, "docx"))
        assert 25 <= result["total"] <= 50 and result["band"] == "Needs work"

    def test_scanned_resume_scores_zero(self, scanned_pdf) -> None:
        assert _score(parse_resume(scanned_pdf, "pdf"))["total"] == 0

    def test_good_beats_two_column_beats_weak(self, good_pdf, two_column_pdf, weak_docx) -> None:
        good = _score(parse_resume(good_pdf, "pdf"))["total"]
        two_column = _score(parse_resume(two_column_pdf, "pdf"))["total"]
        weak = _score(parse_resume(weak_docx, "docx"))["total"]
        assert good > two_column > weak

    def test_structure_is_explainable(self, weak_docx) -> None:
        result = _score(parse_resume(weak_docx, "docx"))
        for name, parameter in result["parameters"].items():
            assert parameter["max"] == config.SCORE_WEIGHTS[name]
            assert parameter["score"] == pytest.approx(sum(c["points"] for c in parameter["evidence"]))
            assert all(c["detail"] and 0 <= c["points"] <= c["max"] for c in parameter["evidence"])
        assert result["total"] == round(sum(p["score"] for p in result["parameters"].values()))

    def test_deterministic(self, two_column_pdf) -> None:
        parsed = parse_resume(two_column_pdf, "pdf")
        assert _score(parsed) == _score(parsed)

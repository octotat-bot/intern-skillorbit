"""Tests for ATS keyword matching, coverage, TF-IDF and penalties."""

from __future__ import annotations

import pytest

from app import config
from app.services.ats import analyze_ats, collect_skills, format_penalty, keyword_score, tfidf_similarity, tokenize
from app.services.parser import parse_resume
from app.services.roles import UnknownRoleError

CLEAN = {"score": 100, "issues": []}


def _labels(items: list[dict]) -> list[str]:
    return [item["label"] for item in items]


def test_full_must_have_coverage() -> None:
    sections = {"skills": "SQL, Python, Excel, Tableau, statistics, data visualization, pandas"}
    result = analyze_ats(sections, "data_analyst", CLEAN)
    assert result["must_have_coverage"] == 1.0
    assert result["missing_must_have"] == []


def test_any_of_alternative_satisfies_requirement() -> None:
    result = analyze_ats({"skills": "PostgreSQL, Power BI"}, "data_analyst", CLEAN)
    matched = {m["label"]: m for m in result["matched"]}
    assert matched["SQL"]["skills"] == ["PostgreSQL"]
    assert matched["Tableau / Power BI"]["skills"] == ["Power BI"]


def test_missing_must_haves_sorted_by_weight() -> None:
    result = analyze_ats({"skills": "Docker"}, "data_analyst", CLEAN)
    weights = [m["weight"] for m in result["missing_must_have"]]
    assert weights == sorted(weights, reverse=True)
    assert result["missing_must_have"][0]["label"] == "SQL"


def test_matched_items_carry_evidence() -> None:
    result = analyze_ats({"skills": "React", "projects": "Built UI in ReactJS"}, "web_developer", CLEAN)
    react = next(m for m in result["matched"] if m["label"] == "React / Angular / Vue")
    assert react["found_as"] == ["React", "ReactJS"]
    assert react["sections"] == ["skills", "projects"]


def test_intention_context_is_ignored() -> None:
    found, ignored = collect_skills({"summary": "I want to learn Docker and Kubernetes."})
    assert "docker" not in found
    assert {i["skill"] for i in ignored} == {"docker", "kubernetes"}
    assert "want to learn" in ignored[0]["reason"]


def test_other_section_is_ignored_but_real_use_counts() -> None:
    found, ignored = collect_skills({"other": "Hobbies: Python games", "projects": "Built with Docker"})
    assert "python" not in found and "docker" in found
    assert ignored[0]["section"] == "other"


def test_skill_counted_elsewhere_is_not_reported_as_ignored() -> None:
    _, ignored = collect_skills({"other": "Python club", "skills": "Python"})
    assert ignored == []


def test_keyword_score_weighting() -> None:
    assert keyword_score(1.0, 0.0, True) == pytest.approx(100 * config.ATS_MUST_HAVE_WEIGHT)
    assert keyword_score(0.5, 1.0, False) == pytest.approx(50)


def test_format_penalty_is_proportional() -> None:
    penalty = format_penalty({"score": 40, "issues": [{"code": "multi_column"}]})
    assert penalty["points"] == pytest.approx(config.ATS_FORMAT_PENALTY_MAX * 0.6)
    assert penalty["issues"] == ["multi_column"]
    assert format_penalty(CLEAN)["points"] == 0


def test_tokenize_stems_and_drops_stop_words() -> None:
    assert tokenize("The dashboards and visualizations") == ["dashboard", "visual"]


def test_tfidf_prefers_matching_role() -> None:
    text = "Built dashboards in Tableau with SQL and Excel; statistics and A/B testing."
    assert tfidf_similarity(text, "data_analyst") > tfidf_similarity(text, "cloud_engineer")
    assert tfidf_similarity("", "data_analyst") == 0.0


def test_unknown_role() -> None:
    with pytest.raises(UnknownRoleError):
        analyze_ats({}, "astronaut", CLEAN)


class TestFixtures:
    def test_two_column_resume_fits_data_analyst_best(self, two_column_pdf) -> None:
        parsed = parse_resume(two_column_pdf, "pdf")
        scores = {role: analyze_ats(parsed.sections, role, parsed.parse_quality)["ats_score"]
                  for role in ("data_analyst", "web_developer", "cloud_engineer")}
        assert max(scores, key=scores.get) == "data_analyst"

    def test_layout_risk_reduces_score(self, two_column_pdf) -> None:
        parsed = parse_resume(two_column_pdf, "pdf")
        risky = analyze_ats(parsed.sections, "data_analyst", parsed.parse_quality)
        clean = analyze_ats(parsed.sections, "data_analyst", CLEAN)
        assert risky["format_penalty"]["points"] > 0
        assert risky["ats_score"] < clean["ats_score"]

    def test_scanned_resume_scores_zero(self, scanned_pdf) -> None:
        parsed = parse_resume(scanned_pdf, "pdf")
        result = analyze_ats(parsed.sections, "data_analyst", parsed.parse_quality)
        assert result["ats_score"] == 0 and result["matched"] == []

    def test_scores_are_bounded_and_deterministic(self, good_pdf, weak_docx) -> None:
        for data, kind in ((good_pdf, "pdf"), (weak_docx, "docx")):
            parsed = parse_resume(data, kind)
            for role in ("data_analyst", "web_developer", "ai_ml_engineer", "cloud_engineer", "full_stack_developer"):
                first = analyze_ats(parsed.sections, role, parsed.parse_quality)
                assert 0 <= first["ats_score"] <= 100
                assert first == analyze_ats(parsed.sections, role, parsed.parse_quality)

    def test_good_resume_missing_skills_are_real(self, good_pdf) -> None:
        parsed = parse_resume(good_pdf, "pdf")
        result = analyze_ats(parsed.sections, "data_analyst", parsed.parse_quality)
        assert _labels(result["missing_must_have"]) == ["Excel", "Statistics"]
        assert "Python" in result["detected_skills"]

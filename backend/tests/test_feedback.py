"""Tests for the feedback rule engine: every rule fires when it should and only then."""

from __future__ import annotations

import pytest

from app import config
from app.services.ats import analyze_ats
from app.services.feedback import RULES, generate_feedback, rule_catalogue
from app.services.parser import parse_resume
from app.services.scorer import score_resume

CLEAN_QUALITY = {"score": 100, "level": "good", "ats_risk": False, "issues": [], "metrics": {"page_count": 1}}

STRONG_SECTIONS = {
    "contact": "Aarav Sharma\naarav@x.com",
    "summary": "Data analyst focused on SQL and dashboards.",
    "education": "B.Tech in CSE\nIIT Delhi | 2021 - 2025 | CGPA 8.7/10",
    "skills": ("Languages: Python, SQL, R\nTools: Excel, Tableau, Power BI, Git\n"
               "Concepts: Statistics, Data visualization, A/B testing"),
    "experience": ("Data Analyst Intern, Acme | Jan 2024 - Mar 2024\n"
                   "Automated reports with Python and SQL, saving 6 hours a week.\n"
                   "Built a Tableau dashboard with Excel inputs used by 3 teams."),
    "projects": ("Churn Model | Python, Pandas, scikit-learn\nEngineered 25 features reaching 89% accuracy.\n"
                 "Sales Dashboard | SQL, Power BI\nDesigned a dashboard tracking 12 KPIs with statistics.\n"
                 "A/B Test Analyzer | Python, Excel\nAnalyzed 40 experiments for data visualization."),
    "certifications": "Google Data Analytics (2024)",
    "achievements": "Winner, Smart India Hackathon 2023",
}
STRONG_CONTACT = {"name": "Aarav Sharma", "email": "aarav@x.com", "phone": "+91 98765 43210",
                  "linkedin": "linkedin.com/in/aarav", "github": "github.com/aarav"}


def _run(sections=None, contact=None, word_count=400, bullet_styles=("•",), quality=None,
         role="data_analyst") -> dict:
    sections = STRONG_SECTIONS if sections is None else sections
    contact = STRONG_CONTACT if contact is None else contact
    stats = {"word_count": word_count, "bullet_styles": list(bullet_styles)}
    quality = quality or CLEAN_QUALITY
    score = score_resume(sections, contact, stats)
    ats = analyze_ats(sections, role, quality)
    return generate_feedback(sections, contact, stats, quality, score, ats)


def _ids(result: dict) -> set[str]:
    return {item["rule_id"] for item in result["suggestions"]}


def _with(**changes) -> dict:
    return {**STRONG_SECTIONS, **changes}


def _without(*names) -> dict:
    return {k: v for k, v in STRONG_SECTIONS.items() if k not in names}


def test_catalogue_has_at_least_25_unique_rules() -> None:
    ids = [r["id"] for r in rule_catalogue()]
    assert len(ids) >= 25 and len(ids) == len(set(ids))
    assert {r["priority"] for r in rule_catalogue()} <= set(config.PRIORITY_ORDER)


def test_strong_resume_triggers_almost_nothing() -> None:
    result = _run()
    assert _ids(result) <= {"K05"}   # only optional nice-to-have suggestions


# Each case: (rule id, keyword arguments for _run that should trigger it).
TRIGGERS = {
    "C01": dict(contact={**STRONG_CONTACT, "email": None}),
    "C02": dict(contact={**STRONG_CONTACT, "phone": None}),
    "C03": dict(contact={**STRONG_CONTACT, "linkedin": None}),
    "C04": dict(contact={**STRONG_CONTACT, "github": None}),
    "C05": dict(contact={**STRONG_CONTACT, "name": None}),
    "S01": dict(sections=_without("experience")),
    "S02": dict(sections=_without("projects")),
    "S03": dict(sections=_without("skills")),
    "S04": dict(sections=_without("education")),
    "S05": dict(sections=_without("summary")),
    "S06": dict(sections={"certifications": "AWS", **_without("certifications")}),
    "S07": dict(sections=_without("certifications")),
    "S08": dict(sections=_without("achievements")),
    "K01": dict(sections=_with(skills="Python, SQL, R, Excel, Tableau, Statistics")),
    "K02": dict(sections=_with(skills="Python, SQL")),
    "K03": dict(sections=_with(skills=", ".join(f"Tool{i}" for i in range(40)))),
    "K04": dict(role="cloud_engineer"),   # strong analyst resume has no Kubernetes
    "K06": dict(sections=_with(skills="Languages: Python, SQL, Go, Rust, Kotlin\nTools: Docker, Jira")),
    "P01": dict(sections=_with(projects="Churn Model | Python\nBuilt a model with 89% accuracy.")),
    "P02": dict(sections=_with(projects="Churn Model | Python\nBuilt a churn model.")),
    "P03": dict(sections=_with(projects="Churn Model\nBuilt a model with 89% accuracy.")),
    "P04": dict(sections=_with(projects="Churn Model | Python\nA model with 89% accuracy.")),
    "P05": dict(sections=_with(projects="Churn Model | Python\nSales Dashboard | SQL")),
    "P06": dict(sections=_with(projects="\n".join(f"Project {i} | Python\nBuilt thing {i} for 5 users." for i in range(7)))),
    "X01": dict(sections=_with(experience="Intern, Acme | Jan 2024 - Mar 2024\nBuilt internal reports with SQL.")),
    "X02": dict(sections=_with(experience="Intern, Acme | Jan 2024 - Mar 2024\nHelped the team with 3 reports.")),
    "E01": dict(sections=_with(education="B.Tech in CSE, CGPA 8.7/10")),
    "E02": dict(sections=_with(education="B.Tech in CSE\nIIT Delhi | 2021 - 2025")),
    "Q01": dict(word_count=80),
    "Q02": dict(word_count=2000),
    "Q03": dict(sections=_with(summary="I am a data analyst and my focus is SQL. I love it.")),
    "Q04": dict(sections=_with(summary="Hard worker and team player.")),
    "Q05": dict(bullet_styles=("•", "-")),
    "Q06": dict(sections=_with(achievements="Winner, Hackathon, January 2023")),
    "Q07": dict(sections=_with(experience="Intern, Acme | Jan 2024 - Mar 2024\nBuilt " + "very " * 35 + "long report for 3 teams.")),
    "Q08": dict(sections=_with(experience="Intern, Acme | Jan 2024\nBuilt A for 2 teams.\nBuilt B for 3 teams.\nBuilt C for 4 teams.")),
    "A01": dict(quality={**CLEAN_QUALITY, "score": 75, "level": "fair", "issues": [
        {"code": "multi_column", "severity": "high", "message": "Multi-column", "evidence": "page 1"}]}),
    "A02": dict(sections={"contact": "Jo", "summary": "Gardening, cooking, travel, chess and poetry. " * 6}),
    "A03": dict(sections=_with(summary="Analyst who wants to learn Kubernetes.")),
}


def test_every_rule_has_a_trigger_case() -> None:
    untested = {r.id for r in RULES} - set(TRIGGERS) - {"K05"}   # K05 fires on STRONG already
    assert untested == set()


@pytest.mark.parametrize("rule_id", sorted(TRIGGERS))
def test_rule_fires(rule_id: str) -> None:
    result = _run(**TRIGGERS[rule_id])
    items = [i for i in result["suggestions"] if i["rule_id"] == rule_id]
    assert items, f"{rule_id} did not fire; fired: {sorted(_ids(result))}"
    item = items[0]
    assert item["suggestion"] and item["evidence"] and item["title"]
    assert item["estimated_impact"]["target"] in {"score", "ats", "readability"}
    assert item["estimated_impact"]["points"] >= 0


def test_rule_fires_on_baseline_k05() -> None:
    k05 = next(i for i in _run()["suggestions"] if i["rule_id"] == "K05")
    assert k05["estimated_impact"]["target"] == "ats" and k05["estimated_impact"]["points"] > 0


def test_missing_must_have_gives_one_suggestion_per_skill() -> None:
    result = _run(sections=_with(skills="Languages: Python, R\nTools: Git, Docker, Linux"),
                  role="cloud_engineer")
    titles = [i["title"] for i in result["suggestions"] if i["rule_id"] == "K04"]
    assert "Missing must-have skill: Kubernetes" in titles
    assert len(titles) == len(set(titles))


def test_score_impact_matches_scorer_gap() -> None:
    result = _run(contact={**STRONG_CONTACT, "phone": None})
    phone = next(i for i in result["suggestions"] if i["rule_id"] == "C02")
    assert phone["estimated_impact"] == {"points": config.CONTACT_PHONE_POINTS, "target": "score"}


def test_sorted_by_priority_then_impact(weak_docx) -> None:
    parsed = parse_resume(weak_docx, "docx")
    score = score_resume(parsed.sections, parsed.contact, parsed.stats)
    ats = analyze_ats(parsed.sections, "data_analyst", parsed.parse_quality)
    items = generate_feedback(parsed.sections, parsed.contact, parsed.stats, parsed.parse_quality, score, ats)["suggestions"]
    keys = [(config.PRIORITY_ORDER[i["priority"]], -i["estimated_impact"]["points"]) for i in items]
    assert keys == sorted(keys)
    assert items[0]["priority"] == "high"


def test_cap_and_counts() -> None:
    result = _run(sections={"contact": "x"}, contact={}, word_count=10, role="full_stack_developer")
    assert result["shown"] == min(result["total"], config.FEEDBACK_MAX_SUGGESTIONS)
    assert sum(result["by_priority"].values()) == result["total"]


def test_unreadable_resume_gets_only_the_formatting_fix(scanned_pdf) -> None:
    parsed = parse_resume(scanned_pdf, "pdf")
    score = score_resume(parsed.sections, parsed.contact, parsed.stats)
    ats = analyze_ats(parsed.sections, "web_developer", parsed.parse_quality)
    result = generate_feedback(parsed.sections, parsed.contact, parsed.stats, parsed.parse_quality, score, ats)
    assert [i["rule_id"] for i in result["suggestions"]] == ["A01"]
    assert "text-based PDF" in result["suggestions"][0]["suggestion"]


def test_deterministic(weak_docx) -> None:
    assert _run(sections=_without("projects")) == _run(sections=_without("projects"))

"""Unit tests for text-level parsing: normalisation, sections, contact, name."""

from __future__ import annotations

import pytest

from app.services.extract import ExtractionResult
from app.services.parser import (
    assess_parse_quality,
    compute_stats,
    detect_sections,
    extract_contact,
    find_phone,
    guess_name,
    match_heading,
    normalize_text,
)


class TestNormalizeText:
    def test_strips_varied_bullet_styles_and_records_them(self) -> None:
        result = normalize_text("• Built X\n● Led Y\n- Wrote Z\n* Shipped W\n▪Tested V")
        assert result.text.split("\n") == ["Built X", "Led Y", "Wrote Z", "Shipped W", "Tested V"]
        assert result.bullet_line_count == 5
        assert result.bullet_styles == sorted(["•", "●", "-", "*", "▪"])

    def test_removes_invisible_private_use_and_control_characters(self) -> None:
        result = normalize_text("Py​thon﻿ email\x0c")
        assert result.text == "Python email"

    def test_fixes_ligatures_quotes_and_whitespace(self) -> None:
        result = normalize_text("ﬁnance   “team”\tlead’s")
        assert result.text == "finance \"team\" lead's"

    def test_collapses_blank_lines_and_trims(self) -> None:
        assert normalize_text("\n\nA\n\n\n\nB\n\n").text == "A\n\nB"

    def test_hyphenated_words_and_negative_numbers_are_not_bullets(self) -> None:
        assert normalize_text("-5% churn").text == "-5% churn"
        assert normalize_text("e-commerce site").text == "e-commerce site"

    def test_empty_input(self) -> None:
        result = normalize_text("")
        assert (result.text, result.bullet_line_count) == ("", 0)


class TestMatchHeading:
    @pytest.mark.parametrize("line, section", [
        ("EDUCATION", "education"),
        ("Work Experience", "experience"),
        ("Technical Skills:", "skills"),
        ("Skills & Tools", "skills"),
        ("INTERNSHIPS", "experience"),
        ("Career Objective", "summary"),
        ("Awards and Achievements", "achievements"),
        ("Licenses & Certifications", "certifications"),
        ("Hobbies", "other"),
        ("TECHNICAL SKILLS & PROFICIENCIES", "skills"),   # keyword rule, ALL CAPS
        ("Relevant Coursework & Projects:", "projects"),  # keyword rule, colon
    ])
    def test_recognises_headings(self, line: str, section: str) -> None:
        assert match_heading(line) == (section, "")

    def test_inline_heading_returns_content(self) -> None:
        assert match_heading("Skills: Python, SQL") == ("skills", "Python, SQL")

    @pytest.mark.parametrize("line", [
        "Languages: Python, SQL",          # skill sub-label must not switch section
        "Technologies: React, Node",       # alias without a section keyword
        "Skill Matcher App",               # Title Case project name with keyword
        "Built a skills dashboard for 3 teams",
        "Experience with Python and SQL in production systems daily",
        "",
    ])
    def test_rejects_body_lines(self, line: str) -> None:
        assert match_heading(line) is None


class TestDetectSections:
    def test_splits_in_document_order_with_contact_block(self) -> None:
        text = "Jane Doe\njane@x.com\nEDUCATION\nB.Tech\nSKILLS\nPython\nPROJECTS\nApp"
        sections = detect_sections(text)
        assert list(sections) == ["contact", "education", "skills", "projects"]
        assert sections["contact"] == "Jane Doe\njane@x.com"

    def test_merges_repeated_headings(self) -> None:
        sections = detect_sections("PROJECTS\nA\nSKILLS\nPython\nPROJECTS\nB")
        assert sections["projects"] == "A\nB"

    def test_other_bucket_keeps_unscored_content_out(self) -> None:
        sections = detect_sections("SKILLS\nPython\nHOBBIES\nChess")
        assert sections == {"skills": "Python", "other": "Chess"}

    def test_skill_sub_labels_stay_in_skills(self) -> None:
        sections = detect_sections("SKILLS\nLanguages: Python\nTools: Git\nPROJECTS\nX")
        assert sections["skills"] == "Languages: Python\nTools: Git"

    def test_inline_heading_content_is_kept(self) -> None:
        assert detect_sections("Skills: Python, SQL\nGit")["skills"] == "Python, SQL\nGit"

    def test_heading_without_body_is_still_reported(self) -> None:
        assert detect_sections("SKILLS\nCERTIFICATIONS")["skills"] == ""

    def test_no_headings_means_contact_only(self) -> None:
        assert list(detect_sections("Just some text\nmore text")) == ["contact"]

    def test_empty_text(self) -> None:
        assert detect_sections("") == {}


class TestContact:
    def test_extracts_all_fields(self) -> None:
        text = ("Jane Doe\njane.doe@mail.co | +91 98765 43210\n"
                "https://www.linkedin.com/in/jane-doe/ | https://github.com/janedoe")
        contact = extract_contact(text, [], text)
        assert contact["email"] == "jane.doe@mail.co"
        assert contact["phone"] == "+91 98765 43210"
        assert contact["linkedin"] == "https://www.linkedin.com/in/jane-doe"
        assert contact["github"] == "https://github.com/janedoe"

    def test_finds_profiles_only_present_as_hyperlink_targets(self) -> None:
        contact = extract_contact("LinkedIn | GitHub", ["https://linkedin.com/in/x-y", "mailto:a@b.io"], "")
        assert contact["linkedin"] == "https://linkedin.com/in/x-y"
        assert contact["email"] == "a@b.io"

    def test_missing_fields_are_none(self) -> None:
        contact = extract_contact("No contact here", [], "")
        assert all(contact[k] is None for k in ("email", "phone", "linkedin", "github"))

    @pytest.mark.parametrize("text, expected", [
        ("Call (555) 123-4567 now", "(555) 123-4567"),
        ("+1-555-123-4567", "+1-555-123-4567"),
        ("9876543210", "9876543210"),
        ("2021 - 2025 | CGPA 8.7", None),          # a date range is not a phone
        ("May 2019 - 2023 2020", None),
        ("Served 10,000+ requests", None),
    ])
    def test_phone_detection(self, text: str, expected: str | None) -> None:
        assert find_phone(text) == expected


class TestGuessName:
    def test_title_case_name(self) -> None:
        assert guess_name("Aarav Sharma\naarav@x.com")["name"] == "Aarav Sharma"

    def test_all_caps_name_is_title_cased(self) -> None:
        assert guess_name("PRIYA NAIR\npriya@x.com")["name"] == "Priya Nair"

    def test_name_label_and_job_title_are_stripped(self) -> None:
        assert guess_name("RESUME\nName: Rohit Kumar")["name"] == "Rohit Kumar"
        assert guess_name("Meera Iyer | Data Analyst")["name"] == "Meera Iyer"

    def test_skips_contact_lines_and_headings(self) -> None:
        result = guess_name("jane@x.com | 9876543210\nProfessional Summary")
        assert result == {"name": None, "name_source": None}

    def test_reports_source(self) -> None:
        assert guess_name("John Smith")["name_source"] in {"spacy", "heuristic"}


def _quality(text: str, **extraction: object) -> dict:
    normalized = normalize_text(text)
    result = ExtractionResult(text=text, extractor="test", page_count=1, **extraction)
    return assess_parse_quality(
        normalized.text, detect_sections(normalized.text), result, compute_stats(normalized)
    )


_SOLID_RESUME = "\n".join(
    ["EDUCATION", "B.Tech in Computer Science, Example University, 2021 - 2025"]
    + ["SKILLS", "Python, SQL, Pandas, NumPy, scikit-learn, Tableau, Git, Docker"]
    + ["PROJECTS"] + [f"Built and deployed analytics project number {i} used by many students" for i in range(8)]
)


class TestParseQuality:
    def test_clean_text_has_no_issues(self) -> None:
        quality = _quality(_SOLID_RESUME)
        assert quality["issues"] == [] and quality["score"] == 100

    def test_short_line_fragments_are_flagged(self) -> None:
        words = "Python SQL led team of four built data pipeline for sales and ops".split()
        quality = _quality(_SOLID_RESUME + "\n" + "\n".join(words * 2))
        codes = [i["code"] for i in quality["issues"]]
        assert "fragmented_text" in codes
        assert "very short" in quality["issues"][codes.index("fragmented_text")]["evidence"]

    def test_lines_broken_mid_sentence_are_flagged(self) -> None:
        broken = "\n".join(
            ["Developed a dashboard that tracked the", "weekly revenue numbers for the regional",
             "sales teams across three different", "business units in the company"] * 5
        )
        codes = [i["code"] for i in _quality(_SOLID_RESUME + "\n" + broken)["issues"]]
        assert "fragmented_text" in codes

    def test_few_sections_flagged(self) -> None:
        text = "SKILLS\n" + " ".join(["Python"] * 100)
        codes = [i["code"] for i in _quality(text)["issues"]]
        assert codes == ["few_sections"]

    def test_images_in_readable_document_are_a_low_risk(self) -> None:
        quality = _quality(_SOLID_RESUME, image_count=2)
        assert [(i["code"], i["severity"]) for i in quality["issues"]] == [("images", "low")]
        assert quality["level"] == "good"

    def test_score_never_goes_below_zero(self) -> None:
        quality = _quality("", image_count=1, table_count=2, multi_column_pages=[1])
        assert quality["score"] == 0 and quality["level"] == "poor"

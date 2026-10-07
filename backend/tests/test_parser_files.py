"""Parser tests over real PDF/DOCX fixtures, including failure cases."""

from __future__ import annotations

import pytest

from app.services import extract as extract_module
from app.services.parser import ParseError, parse_resume
from tests.fixtures import resumes

ALL_SECTIONS = ["contact", "summary", "education", "skills", "experience",
                "projects", "certifications", "achievements"]


def _issue_codes(parsed) -> list[str]:
    return [issue["code"] for issue in parsed.parse_quality["issues"]]


class TestGoodResume:
    @pytest.mark.parametrize("fixture, file_type", [("good_pdf", "pdf"), ("good_docx", "docx")])
    def test_all_sections_and_contact_found(self, request, fixture: str, file_type: str) -> None:
        parsed = parse_resume(request.getfixturevalue(fixture), file_type)
        assert list(parsed.sections) == ALL_SECTIONS
        assert parsed.contact["email"] == "aarav.sharma@example.com"
        assert parsed.contact["phone"] == "+91 98765 43210"
        assert parsed.contact["linkedin"] == "linkedin.com/in/aarav-sharma"
        assert parsed.contact["github"] == "github.com/aaravsharma"
        assert parsed.contact["name"] == "Aarav Sharma"

    @pytest.mark.parametrize("fixture, file_type", [("good_pdf", "pdf"), ("good_docx", "docx")])
    def test_clean_parse_has_no_ats_risk(self, request, fixture: str, file_type: str) -> None:
        quality = parse_resume(request.getfixturevalue(fixture), file_type).parse_quality
        assert quality["issues"] == []
        assert (quality["score"], quality["level"], quality["ats_risk"]) == (100, "good", False)

    def test_pdf_and_docx_yield_the_same_sections(self, good_pdf, good_docx) -> None:
        assert parse_resume(good_pdf, "pdf").sections == parse_resume(good_docx, "docx").sections

    def test_parsing_is_deterministic(self, good_pdf) -> None:
        assert parse_resume(good_pdf, "pdf").to_dict() == parse_resume(good_pdf, "pdf").to_dict()

    def test_bullets_are_stripped_and_counted(self, good_docx) -> None:
        parsed = parse_resume(good_docx, "docx")
        assert "•" not in parsed.clean_text
        assert parsed.stats["bullet_line_count"] == 10
        assert parsed.stats["bullet_styles"] == ["•"]
        assert "• Automated" in parsed.raw_text  # raw text is kept untouched

    def test_skill_sub_labels_stay_in_skills(self, good_pdf) -> None:
        skills = parse_resume(good_pdf, "pdf").sections["skills"]
        assert skills.startswith("Languages: Python, SQL")
        assert "Databases: PostgreSQL, MongoDB" in skills


class TestWeakResume:
    def test_detects_missing_content(self, weak_docx) -> None:
        parsed = parse_resume(weak_docx, "docx")
        assert "experience" not in parsed.sections
        assert parsed.contact["name"] == "Rohit Kumar"
        assert parsed.contact["email"] == "rohit123@gmail.com"
        assert parsed.contact["phone"] is None and parsed.contact["linkedin"] is None
        assert "too_short" in _issue_codes(parsed)
        assert parsed.parse_quality["ats_risk"] is True


class TestTwoColumnResume:
    def test_layout_is_flagged_as_ats_risk(self, two_column_pdf) -> None:
        parsed = parse_resume(two_column_pdf, "pdf")
        assert "multi_column" in _issue_codes(parsed)
        assert parsed.parse_quality["metrics"]["multi_column_pages"] == [1]
        assert parsed.parse_quality["ats_risk"] is True

    def test_columns_are_read_separately_not_interleaved(self, two_column_pdf) -> None:
        parsed = parse_resume(two_column_pdf, "pdf")
        for section in ("skills", "education", "experience", "projects", "certifications"):
            assert section in parsed.sections
        assert "Analyzed 1M+ orders to find churn drivers." in parsed.sections["experience"]
        assert "Tableau" not in parsed.sections["education"]
        assert parsed.contact["phone"] == "+1 (555) 123-4567"


class TestScannedResume:
    def test_image_only_pdf_is_non_extractable(self, scanned_pdf) -> None:
        parsed = parse_resume(scanned_pdf, "pdf")
        assert parsed.clean_text == ""
        assert parsed.sections == {}
        assert _issue_codes(parsed) == ["non_extractable"]
        assert "scanned image" in parsed.parse_quality["issues"][0]["message"]
        assert parsed.parse_quality["level"] == "poor"


class TestOtherLayouts:
    def test_table_layout_is_extracted_and_flagged(self) -> None:
        data = resumes.build_table_docx(
            ["SKILLS", "Python, SQL"], ["EXPERIENCE", "Analyst Intern at Acme"], "Jane Doe"
        )
        parsed = parse_resume(data, "docx")
        assert parsed.sections["skills"] == "Python, SQL"
        assert parsed.sections["experience"] == "Analyst Intern at Acme"
        assert "tables" in _issue_codes(parsed)

    def test_contact_in_docx_page_header_is_found(self) -> None:
        data = resumes.build_docx(resumes.WEAK_RESUME, header="Rohit Kumar | +91 91234 56789")
        assert parse_resume(data, "docx").contact["phone"] == "+91 91234 56789"

    def test_long_document_is_flagged(self) -> None:
        parsed = parse_resume(resumes.build_pdf(resumes.GOOD_RESUME, pages=4), "pdf")
        assert "too_long" in _issue_codes(parsed)

    def test_pdfplumber_failure_falls_back_to_pymupdf(self, good_pdf, monkeypatch) -> None:
        def broken_open(*_args, **_kwargs):
            raise ValueError("simulated pdfplumber crash")

        monkeypatch.setattr(extract_module.pdfplumber, "open", broken_open)
        parsed = parse_resume(good_pdf, "pdf")
        assert parsed.parse_quality["metrics"]["extractor"] == "pymupdf"
        assert "education" in parsed.sections


class TestUnreadableFiles:
    @pytest.mark.parametrize("data, file_type, message", [
        (resumes.CORRUPTED_DOCX, "docx", "corrupted"),
        (resumes.CORRUPTED_PDF, "pdf", "corrupted"),
        (resumes.build_encrypted_pdf(), "pdf", "password-protected"),
        (resumes.build_pdf("line", pages=11), "pdf", "11 pages"),
    ])
    def test_raise_parse_error_with_reason(self, data: bytes, file_type: str, message: str) -> None:
        with pytest.raises(ParseError, match=message):
            parse_resume(data, file_type)

    def test_unsupported_type(self) -> None:
        with pytest.raises(ParseError):
            parse_resume(b"text", "txt")

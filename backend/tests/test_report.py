"""Tests for the PDF report service and GET /api/resumes/<id>/report."""

from __future__ import annotations

import io
from datetime import date

import pymupdf
import pytest

from app.services import rag
from app.services.analysis import build_analysis
from app.services.parser import parse_resume
from app.services.report import build_report_html, render_report_pdf
from tests.fixtures import resumes


def _record(data: bytes, kind: str, filename: str) -> dict:
    return {**parse_resume(data, kind).to_dict(), "id": 1, "filename": filename}


def _text(pdf: bytes) -> str:
    document = pymupdf.open(stream=pdf, filetype="pdf")
    return "\n".join(page.get_text() for page in document)


@pytest.fixture(scope="module")
def weak_analysis() -> dict:
    record = _record(resumes.build_docx(resumes.WEAK_RESUME), "docx", "weak.docx")
    return build_analysis(record, "data_analyst", "rules")


def test_pdf_contains_scores_suggestions_and_breakdown(weak_analysis: dict) -> None:
    pdf = render_report_pdf(weak_analysis)
    assert pdf.startswith(b"%PDF")
    text = " ".join(_text(pdf).split())
    assert f"{weak_analysis['score']['total']} / 100" in text
    assert weak_analysis["feedback"]["suggestions"][0]["title"] in text
    assert "Score breakdown" in text and "Contact information" in text
    assert "Missing must-have skills" in text and "SQL" in text
    assert "transparent heuristic" in text


def test_pages_are_numbered(weak_analysis: dict) -> None:
    document = pymupdf.open(stream=render_report_pdf(weak_analysis), filetype="pdf")
    total = document.page_count
    assert f"Page {total} of {total}" in document[-1].get_text()
    assert document.metadata["title"].startswith("Resume analysis: weak.docx")


def test_resume_text_is_escaped() -> None:
    record = _record(resumes.build_docx("<b>Jane</b> & Co\nSKILLS\n<script>x</script>, Python"), "docx", "<x>.docx")
    html = build_report_html(build_analysis(record, "data_analyst", "rules"), date(2026, 1, 1))
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "&lt;x&gt;.docx" in html


def test_ai_section_reflects_availability(weak_analysis: dict) -> None:
    record = _record(resumes.build_docx(resumes.WEAK_RESUME), "docx", "weak.docx")
    html = build_report_html(build_analysis(record, "data_analyst", "ai"))
    assert "AI insights" in html and "Unavailable" in html
    assert "AI insights" not in build_report_html(weak_analysis)


def test_scanned_resume_report(scanned_pdf) -> None:
    analysis = build_analysis(_record(scanned_pdf, "pdf", "scan.pdf"), "web_developer", "rules")
    text = _text(render_report_pdf(analysis))
    assert "Formatting risks" in text and "scanned image" in text


class TestReportApi:
    def _upload(self, client, data: bytes, name: str) -> int:
        response = client.post("/api/resumes", data={"file": (io.BytesIO(data), name)},
                               content_type="multipart/form-data")
        return response.get_json()["resume_id"]

    def test_download(self, client, good_pdf) -> None:
        resume_id = self._upload(client, good_pdf, "Aarav Resume.pdf")
        response = client.get(f"/api/resumes/{resume_id}/report?role=data_analyst")
        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        assert response.data.startswith(b"%PDF")
        disposition = response.headers["Content-Disposition"]
        assert "attachment" in disposition and "Aarav_Resume-data_analyst-report.pdf" in disposition

    def test_ai_mode_report_never_fails(self, client, good_pdf, monkeypatch) -> None:
        def explode(*_args, **_kwargs):
            raise TimeoutError("provider down")

        monkeypatch.setattr(rag, "generate_ai_feedback", explode)
        resume_id = self._upload(client, good_pdf, "a.pdf")
        response = client.get(f"/api/resumes/{resume_id}/report?role=data_analyst&mode=ai")
        assert response.status_code == 200 and response.data.startswith(b"%PDF")

    @pytest.mark.parametrize("query, status, code", [
        ("", 400, "missing_role"), ("?role=astronaut", 400, "unknown_role"), ("?role=data_analyst&mode=x", 400, "invalid_mode"),
    ])
    def test_bad_parameters(self, client, good_pdf, query: str, status: int, code: str) -> None:
        resume_id = self._upload(client, good_pdf, "a.pdf")
        response = client.get(f"/api/resumes/{resume_id}/report{query}")
        assert response.status_code == status and response.get_json()["error"] == code

    def test_unknown_resume(self, client) -> None:
        response = client.get("/api/resumes/999/report?role=data_analyst")
        assert response.status_code == 404


def test_filename_header_is_exposed_to_the_frontend_origin(client, good_pdf) -> None:
    from app import config

    upload = client.post("/api/resumes", data={"file": (io.BytesIO(good_pdf), "a.pdf")},
                         content_type="multipart/form-data").get_json()
    response = client.get(f"/api/resumes/{upload['resume_id']}/report?role=data_analyst",
                          headers={"Origin": config.CORS_ORIGINS[0]})
    assert "Content-Disposition" in response.headers.get("Access-Control-Expose-Headers", "")

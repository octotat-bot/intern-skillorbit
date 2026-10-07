"""API tests for POST /api/resumes and GET /api/resumes/<id>."""

from __future__ import annotations

import io

import pytest

from app import config
from tests.fixtures import resumes


def _upload(client, data: bytes, filename: str):
    return client.post(
        "/api/resumes",
        data={"file": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
    )


def _assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.get_json()
    assert body["error"] == code
    assert body["message"]


class TestUploadSuccess:
    def test_pdf_upload_returns_receipt(self, client, good_pdf) -> None:
        response = _upload(client, good_pdf, "aarav_resume.pdf")
        assert response.status_code == 201
        body = response.get_json()
        assert isinstance(body["resume_id"], int)
        assert body["filename"] == "aarav_resume.pdf"
        assert body["sections_detected"] == [
            "contact", "summary", "education", "skills", "experience",
            "projects", "certifications", "achievements",
        ]
        assert body["parse_quality"]["level"] == "good"

    def test_docx_upload_with_uppercase_extension(self, client, good_docx) -> None:
        assert _upload(client, good_docx, "RESUME.DOCX").status_code == 201

    def test_filename_is_sanitised(self, client, good_pdf) -> None:
        assert _upload(client, good_pdf, "../../etc/evil.pdf").get_json()["filename"] == "etc_evil.pdf"

    def test_scanned_pdf_is_accepted_with_risk_reported(self, client, scanned_pdf) -> None:
        response = _upload(client, scanned_pdf, "scan.pdf")
        assert response.status_code == 201
        quality = response.get_json()["parse_quality"]
        assert quality["ats_risk"] is True
        assert quality["issues"][0]["code"] == "non_extractable"

    def test_other_sections_are_not_reported(self, client) -> None:
        data = resumes.build_docx("Jane Doe\nSKILLS\nPython\nHOBBIES\nChess")
        assert _upload(client, data, "r.docx").get_json()["sections_detected"] == ["contact", "skills"]


class TestUploadValidation:
    def test_missing_file_field(self, client) -> None:
        response = client.post("/api/resumes", data={}, content_type="multipart/form-data")
        _assert_error(response, 400, "missing_file")

    def test_empty_filename(self, client, good_pdf) -> None:
        _assert_error(_upload(client, good_pdf, ""), 400, "missing_file")

    @pytest.mark.parametrize("filename", ["resume.txt", "resume.doc", "resume", "photo.png"])
    def test_unsupported_extension(self, client, filename: str) -> None:
        _assert_error(_upload(client, b"data", filename), 415, "unsupported_file_type")

    def test_empty_file(self, client) -> None:
        _assert_error(_upload(client, b"", "resume.pdf"), 400, "empty_file")

    def test_file_over_limit_is_rejected(self, client) -> None:
        data = b"%PDF" + b"0" * config.MAX_FILE_SIZE_BYTES
        _assert_error(_upload(client, data, "big.pdf"), 413, "file_too_large")

    def test_request_far_over_limit_is_rejected_by_flask(self, client) -> None:
        data = b"%PDF" + b"0" * (config.MAX_REQUEST_BYTES + 1)
        _assert_error(_upload(client, data, "huge.pdf"), 413, "file_too_large")

    @pytest.mark.parametrize("fixture, filename", [("good_docx", "fake.pdf"), ("good_pdf", "fake.docx")])
    def test_content_must_match_extension(self, request, client, fixture: str, filename: str) -> None:
        _assert_error(_upload(client, request.getfixturevalue(fixture), filename), 415, "content_mismatch")

    @pytest.mark.parametrize("data, filename", [
        (resumes.CORRUPTED_DOCX, "broken.docx"),
        (resumes.CORRUPTED_PDF, "broken.pdf"),
    ])
    def test_corrupted_file(self, client, data: bytes, filename: str) -> None:
        _assert_error(_upload(client, data, filename), 422, "unreadable_file")

    def test_failed_upload_stores_nothing(self, client) -> None:
        _upload(client, resumes.CORRUPTED_DOCX, "broken.docx")
        _assert_error(client.get("/api/resumes/1"), 404, "resume_not_found")


class TestResumeDetail:
    def test_returns_parsed_resume(self, client, good_pdf) -> None:
        resume_id = _upload(client, good_pdf, "a.pdf").get_json()["resume_id"]
        response = client.get(f"/api/resumes/{resume_id}")
        assert response.status_code == 200
        body = response.get_json()
        assert body["resume_id"] == resume_id
        assert body["file_type"] == "pdf"
        assert body["contact"]["email"] == "aarav.sharma@example.com"
        assert body["sections"]["education"].startswith("B.Tech")
        assert "Customer Churn Prediction" in body["text"]
        assert body["stats"]["word_count"] > 0
        assert body["created_at"]

    def test_unknown_id(self, client) -> None:
        _assert_error(client.get("/api/resumes/999"), 404, "resume_not_found")

    def test_non_integer_id_is_404(self, client) -> None:
        assert client.get("/api/resumes/abc").status_code == 404


def test_unexpected_error_returns_generic_json_500(client, good_pdf, monkeypatch) -> None:
    def explode(*_args, **_kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr("app.routes.upload.parse_resume", explode)
    response = _upload(client, good_pdf, "a.pdf")
    _assert_error(response, 500, "internal_error")
    assert "secret" not in response.get_json()["message"]

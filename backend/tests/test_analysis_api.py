"""API tests for GET /api/resumes/<id>/analysis."""

from __future__ import annotations

import io

import pytest

from app.services import rag


def _upload(client, data: bytes, name: str) -> int:
    response = client.post("/api/resumes", data={"file": (io.BytesIO(data), name)},
                           content_type="multipart/form-data")
    return response.get_json()["resume_id"]


@pytest.fixture()
def resume_id(client, good_pdf) -> int:
    return _upload(client, good_pdf, "good.pdf")


def test_rules_analysis(client, resume_id: int) -> None:
    response = client.get(f"/api/resumes/{resume_id}/analysis?role=data_analyst")
    assert response.status_code == 200
    body = response.get_json()
    assert body["mode"] == "rules"
    assert body["role"] == {"id": "data_analyst", "name": "Data Analyst"}
    assert body["score"]["total"] == 100
    assert 0 <= body["ats"]["ats_score"] <= 100
    assert body["feedback"]["total"] == len(body["feedback"]["suggestions"])
    assert "ai_available" not in body


def test_same_input_same_output(client, resume_id: int) -> None:
    url = f"/api/resumes/{resume_id}/analysis?role=web_developer"
    assert client.get(url).get_json() == client.get(url).get_json()


def test_role_changes_ats_not_score(client, resume_id: int) -> None:
    analyst = client.get(f"/api/resumes/{resume_id}/analysis?role=data_analyst").get_json()
    cloud = client.get(f"/api/resumes/{resume_id}/analysis?role=cloud_engineer").get_json()
    assert analyst["score"] == cloud["score"]
    assert analyst["ats"]["ats_score"] > cloud["ats"]["ats_score"]


@pytest.mark.parametrize("query, code", [
    ("", "missing_role"),
    ("?role=astronaut", "unknown_role"),
    ("?role=data_analyst&mode=magic", "invalid_mode"),
])
def test_bad_parameters(client, resume_id: int, query: str, code: str) -> None:
    response = client.get(f"/api/resumes/{resume_id}/analysis{query}")
    assert response.status_code == 400 and response.get_json()["error"] == code


def test_unknown_resume(client) -> None:
    response = client.get("/api/resumes/999/analysis?role=data_analyst")
    assert response.status_code == 404 and response.get_json()["error"] == "resume_not_found"


def test_ai_mode_failure_falls_back_to_rules(client, resume_id: int, monkeypatch) -> None:
    def explode(*_args, **_kwargs):
        raise TimeoutError("provider timed out")

    monkeypatch.setattr(rag, "generate_ai_feedback", explode)
    body = client.get(f"/api/resumes/{resume_id}/analysis?role=data_analyst&mode=ai").get_json()
    rules = client.get(f"/api/resumes/{resume_id}/analysis?role=data_analyst").get_json()
    assert body["ai_available"] is False
    assert "TimeoutError" in body["ai_unavailable_reason"]
    assert body["generated_feedback"] is None
    assert body["score"] == rules["score"] and body["feedback"] == rules["feedback"]


def test_scanned_resume_analysis(client, scanned_pdf) -> None:
    resume = _upload(client, scanned_pdf, "scan.pdf")
    body = client.get(f"/api/resumes/{resume}/analysis?role=web_developer").get_json()
    assert body["score"]["total"] == 0 and body["ats"]["ats_score"] == 0
    assert [s["rule_id"] for s in body["feedback"]["suggestions"]] == ["A01"]


def test_json_preserves_document_and_parameter_order(client, resume_id: int) -> None:
    body = client.get(f"/api/resumes/{resume_id}/analysis?role=data_analyst").get_json()
    assert list(body["score"]["parameters"]) == ["contact", "structure", "skills", "projects", "education", "quality"]
    sections = client.get(f"/api/resumes/{resume_id}").get_json()["sections"]
    assert list(sections)[:3] == ["contact", "summary", "education"]

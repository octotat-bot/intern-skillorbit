"""API test for GET /api/roles."""

from __future__ import annotations


def test_lists_roles_with_requirements(client) -> None:
    response = client.get("/api/roles")
    assert response.status_code == 200
    roles = response.get_json()["roles"]
    assert [r["id"] for r in roles] == [
        "data_analyst", "web_developer", "ai_ml_engineer", "cloud_engineer", "full_stack_developer",
    ]
    analyst = roles[0]
    assert analyst["name"] == "Data Analyst" and analyst["description"]
    assert analyst["must_have"][0] == {
        "label": "SQL", "weight": 3.0,
        "alternatives": ["SQL", "MySQL", "PostgreSQL", "SQL Server", "SQLite", "BigQuery"],
    }
    assert "Pandas" in analyst["nice_to_have"]

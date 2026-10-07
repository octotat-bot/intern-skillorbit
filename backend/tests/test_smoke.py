"""App-level smoke tests: factory, config sanity, and not-yet-built endpoints."""

from __future__ import annotations

import json

from app import config


def test_health_endpoint(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_score_weights_sum_to_100() -> None:
    assert sum(config.SCORE_WEIGHTS.values()) == 100


def test_roles_file_lists_required_roles() -> None:
    roles = json.loads(config.ROLES_FILE.read_text())["roles"]
    assert {r["id"] for r in roles} == {
        "data_analyst", "web_developer", "ai_ml_engineer",
        "cloud_engineer", "full_stack_developer",
    }


def test_unknown_route_returns_json_404(client) -> None:
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


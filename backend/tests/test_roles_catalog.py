"""Tests for roles.json loading and validation."""

from __future__ import annotations

import copy
import json

import pytest

from app import config
from app.services.roles import RoleCatalogError, UnknownRoleError, get_role, load_catalog, parse_catalog

REQUIRED_ROLES = {"data_analyst", "web_developer", "ai_ml_engineer", "cloud_engineer", "full_stack_developer"}


@pytest.fixture()
def raw() -> dict:
    return json.loads(config.ROLES_FILE.read_text())


def test_shipped_catalogue_has_required_roles() -> None:
    assert set(load_catalog().roles) == REQUIRED_ROLES


def test_every_role_is_complete() -> None:
    for role in load_catalog().roles.values():
        assert role.description and role.must_have and role.nice_to_have
        assert all(req.weight > 0 and req.any_of for req in role.must_have)


def test_spec_aliases_resolve() -> None:
    aliases = load_catalog().aliases()
    assert aliases["js"] == "javascript"
    assert aliases["reactjs"] == "react"
    assert aliases["ml"] == "machine learning"


def test_display_names() -> None:
    catalog = load_catalog()
    assert catalog.display("node.js") == "Node.js"
    assert catalog.display("pandas") == "Pandas"


def test_get_role() -> None:
    assert get_role("data_analyst").name == "Data Analyst"
    with pytest.raises(UnknownRoleError):
        get_role("astronaut")


def _mutate(raw: dict, change) -> dict:
    data = copy.deepcopy(raw)
    change(data)
    return data


@pytest.mark.parametrize("change, message", [
    (lambda d: d["roles"].append(copy.deepcopy(d["roles"][0])), "Duplicate role ids"),
    (lambda d: d["roles"][0]["must_have"][0].update(weight=0), "positive weight"),
    (lambda d: d["roles"][0]["must_have"][0].update(any_of=[]), "empty any_of"),
    (lambda d: d["roles"][0].update(must_have=[]), "must_have is empty"),
    (lambda d: d["common_aliases"].update(foo="not-a-skill"), "unknown skill"),
    (lambda d: d["case_sensitive_terms"].update(X="not-a-skill"), "unknown skill"),
    (lambda d: d["roles"][1]["aliases"].update(js="python"), "maps to both"),
    (lambda d: d["roles"][0].pop("name"), "Missing field"),
])
def test_invalid_catalogues_are_rejected(raw: dict, change, message: str) -> None:
    with pytest.raises(RoleCatalogError, match=message):
        parse_catalog(_mutate(raw, change))

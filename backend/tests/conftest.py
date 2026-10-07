"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from tests.fixtures import resumes


@pytest.fixture()
def app(tmp_path, monkeypatch) -> Iterator[Flask]:
    """App wired to a throwaway SQLite database."""
    from app import config, create_app

    monkeypatch.setattr(config, "DATABASE_PATH", tmp_path / "test.db")
    yield create_app()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Flask test client."""
    return app.test_client()


# Binary fixture resumes are built once per session; building is deterministic.
@pytest.fixture(scope="session")
def good_pdf() -> bytes:
    return resumes.build_pdf(resumes.GOOD_RESUME)


@pytest.fixture(scope="session")
def good_docx() -> bytes:
    return resumes.build_docx(resumes.GOOD_RESUME)


@pytest.fixture(scope="session")
def weak_docx() -> bytes:
    return resumes.build_docx(resumes.WEAK_RESUME)


@pytest.fixture(scope="session")
def two_column_pdf() -> bytes:
    return resumes.build_two_column_pdf(
        resumes.TWO_COLUMN_HEADER, resumes.TWO_COLUMN_LEFT, resumes.TWO_COLUMN_RIGHT
    )


@pytest.fixture(scope="session")
def scanned_pdf() -> bytes:
    return resumes.build_scanned_pdf()

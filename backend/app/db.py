"""SQLite persistence layer (stdlib ``sqlite3``).

Stores one row per uploaded resume. The original file is never written to
disk: only the extracted text and the parser's structured output are kept.
Analysis results are recomputed deterministically on demand, not persisted.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS resumes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT    NOT NULL,
    file_type     TEXT    NOT NULL,   -- "pdf" | "docx"
    raw_text      TEXT    NOT NULL,   -- text exactly as extracted
    clean_text    TEXT    NOT NULL,   -- normalised text used for analysis
    sections      TEXT    NOT NULL,   -- JSON {section_name: text}, document order
    contact       TEXT    NOT NULL,   -- JSON contact details
    parse_quality TEXT    NOT NULL,   -- JSON parse-quality report
    stats         TEXT    NOT NULL,   -- JSON text statistics
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

_JSON_FIELDS: tuple[str, ...] = ("sections", "contact", "parse_quality", "stats")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Yield a connection that commits on success and always closes."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not yet exist."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def insert_resume(filename: str, file_type: str, parsed: dict[str, Any]) -> int:
    """Persist a parsed resume.

    Args:
        filename: Sanitised original filename.
        file_type: ``"pdf"`` or ``"docx"``.
        parsed: Output of :meth:`ParsedResume.to_dict`.

    Returns:
        The new resume's integer id.
    """
    row = (
        filename,
        file_type,
        parsed["raw_text"],
        parsed["clean_text"],
        *(json.dumps(parsed[name]) for name in _JSON_FIELDS),
    )
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO resumes (filename, file_type, raw_text, clean_text, "
            "sections, contact, parse_quality, stats) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            row,
        )
        return int(cursor.lastrowid)


def get_resume(resume_id: int) -> dict[str, Any] | None:
    """Fetch a stored resume with JSON columns decoded, or None if absent."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    if row is None:
        return None
    record = dict(row)
    for name in _JSON_FIELDS:
        record[name] = json.loads(record[name])
    return record

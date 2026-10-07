"""Keep the documentation in step with the code."""

from __future__ import annotations

from pathlib import Path

from app.services.feedback import rule_catalogue

DOCS = Path(__file__).resolve().parents[2] / "docs"


def test_every_rule_is_documented() -> None:
    text = (DOCS / "ai_logic.md").read_text()
    missing = [r["id"] for r in rule_catalogue() if f"| {r['id']} | {r['title']} |" not in text]
    assert missing == [], f"Regenerate the rule table in docs/ai_logic.md for: {missing}"


def test_required_documents_exist() -> None:
    for name in ("architecture.md", "api.md", "ai_logic.md", "evaluation.md", "deployment.md",
                 "report_outline.md", "ppt_outline.md"):
        assert (DOCS / name).stat().st_size > 500, name

"""PDF report generation for an analysis.

The report is built as HTML (every value from the resume is escaped) and laid
out into A4 pages with PyMuPDF's Story API, so no extra dependency is needed.
Page numbers are stamped in a second pass once the page count is known.
"""

from __future__ import annotations

import io
from datetime import date
from html import escape
from typing import Any

import pymupdf

from app import config

_CSS = """
body { font-family: sans-serif; font-size: 9.5pt; color: #1a1a1a; line-height: 1.4; }
h1 { font-size: 20pt; margin: 0 0 2pt 0; color: #0a0a0a; }
h2 { font-size: 12.5pt; margin: 16pt 0 6pt 0; color: #0a0a0a; border-bottom: 1px solid #dddddd; padding-bottom: 3pt; }
h3 { font-size: 10.5pt; margin: 10pt 0 3pt 0; color: #0a0a0a; }
p { margin: 0 0 5pt 0; }
.muted { color: #6b6b6b; }
.small { font-size: 8.5pt; }
.big { font-size: 26pt; font-weight: bold; color: #0a0a0a; }
table { border-collapse: collapse; width: 100%; margin: 2pt 0 6pt 0; }
th { text-align: left; font-size: 8.5pt; color: #6b6b6b; border-bottom: 1px solid #cccccc; padding: 3pt 4pt; }
td { border-bottom: 1px solid #eeeeee; padding: 3pt 4pt; vertical-align: top; }
.num { text-align: right; white-space: nowrap; }
.high { color: #b42323; font-weight: bold; }
.medium { color: #8a5a00; font-weight: bold; }
.low { color: #52525b; font-weight: bold; }
.pass { color: #006300; }
.partial { color: #8a5a00; }
.fail { color: #b42323; }
"""

_STATUS_LABEL = {"pass": "earned", "partial": "partly earned", "fail": "missed"}


def _e(value: Any) -> str:
    """HTML-escape any value."""
    return escape(str(value))


def _summary(a: dict[str, Any]) -> str:
    """Headline numbers: resume score, ATS score, parse quality, suggestion counts."""
    score, ats, quality, fb = a["score"], a["ats"], a["parse_quality"], a["feedback"]
    counts = fb["by_priority"]
    return f"""
    <h2>Summary</h2>
    <table>
      <tr><th>Resume score</th><th>ATS match ({_e(ats['role_name'])})</th><th>Parse quality</th><th>Suggestions</th></tr>
      <tr>
        <td><span class="big">{score['total']}</span><span class="muted"> / 100</span><br/>{_e(score['band'])}</td>
        <td><span class="big">{ats['ats_score']}</span><span class="muted"> / 100</span><br/>
            must-have {round(ats['must_have_coverage'] * 100)}%, bonus {round(ats['nice_to_have_coverage'] * 100)}%</td>
        <td><span class="big">{quality['score']}</span><span class="muted"> / 100</span><br/>{_e(quality['level'])}</td>
        <td><span class="big">{fb['total']}</span><br/>{counts['high']} high, {counts['medium']} medium, {counts['low']} low</td>
      </tr>
    </table>"""


def _formatting(quality: dict[str, Any]) -> str:
    """Parse-quality issues, if any."""
    if not quality["issues"]:
        return ""
    rows = "".join(f"<li>{_e(i['message'])} <span class='muted'>({_e(i['evidence'])})</span></li>" for i in quality["issues"])
    return f"<h2>Formatting risks</h2><ul>{rows}</ul><p class='small muted'>These lower the ATS score, not the resume score.</p>"


def _breakdown(parameters: dict[str, Any]) -> str:
    """Every scoring check with its evidence and points."""
    parts = ["<h2>Score breakdown</h2>"]
    for p in parameters.values():
        rows = "".join(
            f"<tr><td class='{c['status']}'>{_e(c['label'])} ({_STATUS_LABEL[c['status']]})</td>"
            f"<td>{_e(c['detail'])}</td><td class='num'>{c['points']} / {c['max']}</td></tr>"
            for c in p["evidence"]
        )
        parts.append(f"<h3>{_e(p['label'])}: {p['score']} / {p['max']}</h3>"
                     f"<table><tr><th width='34%'>Check</th><th width='52%'>Evidence</th><th width='14%' class='num'>Points</th></tr>{rows}</table>")
    return "".join(parts)


def _skills(ats: dict[str, Any]) -> str:
    """Missing must-haves, matched requirements and bonus skills."""
    missing = "".join(
        f"<tr><td>{_e(m['label'])}</td><td>{_e(', '.join(m['alternatives']))}</td><td class='num'>{m['weight']:g}</td></tr>"
        for m in ats["missing_must_have"]
    ) or "<tr><td colspan='3'>Every must-have requirement is covered.</td></tr>"
    matched = "".join(
        f"<tr><td>{_e(m['label'])}</td><td>{_e(', '.join(m['found_as']))}</td><td>{_e(', '.join(m['sections']))}</td></tr>"
        for m in ats["matched"]
    ) or "<tr><td colspan='3'>No requirements matched.</td></tr>"
    bonus = ", ".join(_e(m["label"]) for m in ats["missing_nice_to_have"]) or "All bonus skills found."
    return f"""
    <h2>Skills match: {_e(ats['role_name'])}</h2>
    <h3>Missing must-have skills</h3>
    <table><tr><th>Requirement</th><th>Accepted skills</th><th class='num'>Weight</th></tr>{missing}</table>
    <h3>Matched requirements</h3>
    <table><tr><th>Requirement</th><th>Found as</th><th>Sections</th></tr>{matched}</table>
    <h3>Bonus skills worth adding</h3><p>{bonus}</p>"""


def _suggestions(feedback: dict[str, Any]) -> str:
    """Prioritised suggestions with their evidence."""
    if not feedback["suggestions"]:
        return "<h2>Improvement suggestions</h2><p>No rule found anything to improve.</p>"
    items = []
    for i, s in enumerate(feedback["suggestions"][: config.REPORT_MAX_SUGGESTIONS], start=1):
        impact = s["estimated_impact"]
        unit = {"ats": " ATS points", "score": " points"}.get(impact["target"], "")
        impact_text = f" &middot; +{impact['points']:g}{unit}" if impact["points"] else ""
        evidence = "; ".join(_e(line) for line in s["evidence"])
        items.append(
            f"<p><span class='{s['priority']}'>{i}. {s['priority'].upper()}</span> "
            f"<b>{_e(s['title'])}</b><span class='muted small'>{impact_text} &middot; rule {_e(s['rule_id'])}</span><br/>"
            f"{_e(s['suggestion'])}<br/><span class='muted small'>Evidence: {evidence}</span></p>"
        )
    return "<h2>Improvement suggestions</h2>" + "".join(items)


def _ai(a: dict[str, Any]) -> str:
    """AI insights section (only in AI mode)."""
    if a.get("mode") != "ai":
        return ""
    generated = a.get("generated_feedback")
    if not generated:
        return f"<h2>AI insights</h2><p class='muted'>Unavailable: {_e(a.get('ai_unavailable_reason') or 'not generated')}.</p>"
    parts = ["<h2>AI insights</h2>"]
    if generated.get("summary"):
        parts.append(f"<p>{_e(generated['summary']['text'])} <span class='muted small'>[{_e(', '.join(generated['summary']['chunk_ids']))}]</span></p>")
    for r in generated["bullet_rewrites"]:
        parts.append(f"<p><span class='muted'>Before:</span> {_e(r['original'])}<br/><b>After:</b> {_e(r['rewritten'])} "
                     f"<span class='muted small'>[{_e(', '.join(r['chunk_ids']))}]</span></p>")
    for g in generated["skill_gaps"]:
        parts.append(f"<p><b>{_e(g['skill'])}:</b> {_e(g['explanation'])} <span class='muted small'>[{_e(', '.join(g['chunk_ids']))}]</span></p>")
    parts.append(f"<p class='small muted'>Generated by {_e(generated['model'])} using only the cited knowledge-base sources.</p>")
    return "".join(parts)


def build_report_html(analysis: dict[str, Any], generated_on: date | None = None) -> str:
    """Full report as an HTML document."""
    a = analysis
    contact = a["contact"]
    who = " &middot; ".join(_e(v) for v in (contact.get("name"), contact.get("email")) if v)
    day = (generated_on or date.today()).isoformat()
    return f"""<html><body>
    <h1>Resume analysis report</h1>
    <p class="muted">{_e(a['filename'])}{(' &middot; ' + who) if who else ''}<br/>
    Target role: {_e(a['role']['name'])} &middot; Generated {day} by Smart Resume Analyzer</p>
    {_summary(a)}{_formatting(a['parse_quality'])}{_suggestions(a['feedback'])}{_skills(a['ats'])}
    {_breakdown(a['score']['parameters'])}{_ai(a)}
    <h2>About this report</h2>
    <p class="small muted">The resume score and suggestions come from deterministic rules: the same resume and role
    always give the same result, and every point is backed by the evidence shown. The ATS score is a transparent
    heuristic, not a vendor-verified metric; real applicant tracking systems are configured differently by each employer.</p>
    </body></html>"""


def _layout(html: str) -> bytes:
    """Flow HTML across as many pages as needed."""
    buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(buffer)
    page = pymupdf.paper_rect(config.REPORT_PAGE_SIZE)
    margin = config.REPORT_MARGIN_PT
    body = page + (margin, margin, -margin, -margin)
    story = pymupdf.Story(html=html, user_css=_CSS)
    more = True
    while more:
        device = writer.begin_page(page)
        more, _ = story.place(body)
        story.draw(device)
        writer.end_page()
    writer.close()
    return buffer.getvalue()


def _stamp_page_numbers(pdf: bytes, title: str) -> bytes:
    """Add 'title · Page n of N' to each page footer and set document metadata."""
    document = pymupdf.open(stream=pdf, filetype="pdf")
    total = document.page_count
    for number, page in enumerate(document, start=1):
        y = page.rect.height - config.REPORT_FOOTER_OFFSET_PT
        page.insert_text((config.REPORT_MARGIN_PT, y), f"{title} · Page {number} of {total}",
                         fontsize=7.5, color=(0.45, 0.45, 0.45))
    document.set_metadata({"title": title, "creator": "Smart Resume Analyzer"})
    return document.tobytes(garbage=3, deflate=True)


def render_report_pdf(analysis: dict[str, Any], generated_on: date | None = None) -> bytes:
    """Render an analysis (as returned by the analysis API) to PDF bytes."""
    title = f"Resume analysis: {analysis['filename']} ({analysis['role']['name']})"
    return _stamp_page_numbers(_layout(build_report_html(analysis, generated_on)), title)
